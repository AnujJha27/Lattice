"""Brain + concept domain logic.

The Brain graph for a user is every concept they have a user_concept row for,
plus the edges between those concepts. Canonical concepts are deduplicated by
case-insensitive name (spec §34 step 1-2; embedding/trigram adjudication comes
with the sources phase).
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.db.models import Concept, ConceptEdge, UserConcept
from app.db.models.concept import EdgeType
from app.domain.graph import ensure_acyclic
from app.modules.brain.schemas import (
    BrainEdge,
    BrainGraphResponse,
    BrainNode,
    ConceptCreate,
    ConceptDetail,
    ConceptOut,
)


async def get_or_create_concept(
    session: AsyncSession, payload: ConceptCreate
) -> tuple[Concept, bool]:
    """Dedupe pipeline (spec §34): case-insensitive name match first, then
    semantic match via embeddings (strict threshold — only near-identical
    concepts merge). Falls back to creation when embedding fails."""
    normalized = payload.canonical_name.strip()
    result = await session.execute(
        select(Concept).where(func.lower(Concept.canonical_name) == normalized.lower())
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if payload.domain and not existing.domain:
            existing.domain = payload.domain.strip()
        return existing, False

    # Semantic dedup: "ML" and "Machine Learning" should be one star.
    try:
        from app.providers.embedding import GeminiEmbeddingProvider

        embedder = GeminiEmbeddingProvider()
        [vector] = await embedder.embed([f"{normalized}. {payload.description or ''}"])
        distance_expr = Concept.summary_embedding.cosine_distance(vector)
        nearest = await session.execute(
            select(Concept, distance_expr)
            .where(Concept.summary_embedding.isnot(None))
            .order_by(distance_expr)
            .limit(1)
        )
        row = nearest.first()
        if row is not None:
            candidate, distance = row
            if float(distance) < 0.13:  # near-identical only
                if normalized.lower() not in [a.lower() for a in (candidate.aliases or [])]:
                    candidate.aliases = [*(candidate.aliases or []), normalized]
                return candidate, False
        embedding = vector
    except Exception:  # noqa: BLE001 — embedding outage must not block creation
        embedding = None

    concept = Concept(
        canonical_name=normalized,
        description=payload.description,
        domain=payload.domain.strip() if payload.domain else None,
        difficulty=payload.difficulty,
        scope="GLOBAL",
        summary_embedding=embedding,
    )
    session.add(concept)
    await session.flush()
    return concept, True


async def ensure_user_concept(session: AsyncSession, user_id: uuid.UUID, concept_id: uuid.UUID) -> UserConcept:
    from app.modules.users.routes import ensure_profile

    # The profile mirror must exist before any user-owned row references it.
    await ensure_profile(session, user_id)

    result = await session.execute(
        select(UserConcept).where(
            UserConcept.user_id == user_id, UserConcept.concept_id == concept_id
        )
    )
    user_concept = result.scalar_one_or_none()
    if user_concept is None:
        user_concept = UserConcept(
            user_id=user_id, concept_id=concept_id, interest_score=50
        )
        session.add(user_concept)
        await session.flush()
    return user_concept


async def get_brain_graph(session: AsyncSession, user: CurrentUser) -> BrainGraphResponse:
    rows = await session.execute(
        select(Concept, UserConcept)
        .join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id)
        .order_by(Concept.created_at)
    )
    pairs = rows.all()
    node_ids = {concept.id for concept, _ in pairs}

    edges: list[BrainEdge] = []
    if node_ids:
        edge_rows = await session.execute(
            select(
                ConceptEdge.source_id,
                ConceptEdge.target_id,
                ConceptEdge.type,
                ConceptEdge.confidence,
                ConceptEdge.created_by,
            ).where(
                ConceptEdge.source_id.in_(node_ids), ConceptEdge.target_id.in_(node_ids)
            )
        )
        edges = [
            BrainEdge(source=src, target=dst, type=edge_type.value, confidence=confidence, created_by=created_by)
            for src, dst, edge_type, confidence, created_by in edge_rows.all()
        ]

    return BrainGraphResponse(
        nodes=[
            BrainNode(
                id=concept.id,
                name=concept.canonical_name,
                domain=concept.domain,
                difficulty=concept.difficulty,
                mastery_score=float(state.mastery_score),
                state=state.state.value,
                interest_score=float(state.interest_score),
            )
            for concept, state in pairs
        ],
        edges=edges,
        generated_at=datetime.now(UTC),
    )


async def add_edge(
    session: AsyncSession,
    user_id: uuid.UUID,
    source_id: uuid.UUID,
    target_id: uuid.UUID,
    edge_type: EdgeType,
) -> ConceptEdge:
    """Add an edge after validating the prerequisite DAG. Both endpoints join
    the user's Brain so the new relationship is visible in their graph."""
    if edge_type == EdgeType.PREREQUISITE:
        if source_id == target_id:
            raise ValueError("A concept cannot be its own prerequisite")

        both = await session.execute(
            select(Concept.id).where(or_(Concept.id == source_id, Concept.id == target_id))
        )
        found = {row[0] for row in both.all()}
        if found != {source_id, target_id}:
            raise LookupError("Both concepts must exist")

        edge_rows = await session.execute(
            select(ConceptEdge.source_id, ConceptEdge.target_id).where(
                ConceptEdge.type == EdgeType.PREREQUISITE
            )
        )
        all_edges = [(s, t) for s, t in edge_rows.all()]
        ensure_acyclic(set(), all_edges, (str(source_id), str(target_id)))

    await ensure_user_concept(session, user_id, source_id)
    await ensure_user_concept(session, user_id, target_id)

    edge = ConceptEdge(source_id=source_id, target_id=target_id, type=edge_type, created_by="user")
    session.add(edge)
    await session.flush()
    return edge


def to_detail(concept: Concept, state: UserConcept | None,
              prereqs: list[Concept], dependents: list[Concept],
              related: list[Concept]) -> ConceptDetail:
    return ConceptDetail(
        id=concept.id,
        canonical_name=concept.canonical_name,
        description=concept.description,
        domain=concept.domain,
        difficulty=concept.difficulty,
        prerequisites=[_to_out(c) for c in prereqs],
        dependents=[_to_out(c) for c in dependents],
        related=[_to_out(c) for c in related],
        mastery_score=float(state.mastery_score) if state else 0,
        state=state.state.value if state else "UNSEEN",
        in_brain=state is not None,
    )


def _to_out(concept: Concept) -> ConceptOut:
    return ConceptOut(
        id=concept.id,
        canonical_name=concept.canonical_name,
        description=concept.description,
        domain=concept.domain,
        difficulty=concept.difficulty,
    )

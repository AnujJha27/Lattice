"""Concept CRUD: create with dedupe, detail, prerequisite edges (DAG-validated)."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import AppError, NotFound
from app.db.models import AIGeneration, Concept, ConceptEdge, UserConcept
from app.db.models.concept import EdgeType
from app.db.session import get_session
from app.modules.brain import service
from app.modules.brain.schemas import (
    CombineRequest,
    ConceptCreate,
    ConceptDetail,
    ConceptOut,
    EdgeCreate,
)

router = APIRouter(prefix="/concepts", tags=["concepts"])


@router.post("", response_model=ConceptOut, status_code=status.HTTP_201_CREATED)
async def create_concept(
    payload: ConceptCreate,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> ConceptOut:
    concept, created = await service.get_or_create_concept(session, payload)
    if payload.add_interest:
        await service.ensure_user_concept(session, user.id, concept.id)
    await session.commit()
    _ = created  # callers can diff via response later; kept for future analytics
    return ConceptOut(
        id=concept.id,
        canonical_name=concept.canonical_name,
        description=concept.description,
        domain=concept.domain,
        difficulty=concept.difficulty,
    )


@router.get("/{concept_id}", response_model=ConceptDetail)
async def get_concept(
    concept_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> ConceptDetail:
    result = await session.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if concept is None:
        raise NotFound("concept", concept_id)

    state_result = await session.execute(
        select(UserConcept).where(
            UserConcept.user_id == user.id, UserConcept.concept_id == concept_id
        )
    )
    state = state_result.scalar_one_or_none()

    async def neighbors(direction_source_col, direction_target_col) -> list[Concept]:
        edge_ids = await session.execute(
            select(direction_source_col).where(direction_target_col == concept_id)
        )
        ids = [row[0] for row in edge_ids.all()]
        if not ids:
            return []
        rows = await session.execute(select(Concept).where(Concept.id.in_(ids)))
        return list(rows.scalars().all())

    prereqs = await neighbors(ConceptEdge.source_id, ConceptEdge.target_id)
    dependents = await neighbors(ConceptEdge.target_id, ConceptEdge.source_id)
    related_rows = await session.execute(
        select(Concept)
        .join(ConceptEdge, ConceptEdge.target_id == Concept.id)
        .where(
            ConceptEdge.source_id == concept_id,
            ConceptEdge.type == EdgeType.RELATED_TO,
        )
    )
    related = list(related_rows.scalars().all())

    return service.to_detail(concept, state, prereqs, dependents, related)


@router.post("/{concept_id}/edges", status_code=status.HTTP_201_CREATED)
async def add_edge(
    concept_id: uuid.UUID,
    payload: EdgeCreate,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> dict:
    if payload.type not in EdgeType.__members__:
        raise AppError("invalid_edge_type", f"Unknown edge type '{payload.type}'")
    try:
        await service.add_edge(
            session, user.id, concept_id, payload.target_id, EdgeType(payload.type)
        )
    except ValueError as exc:
        raise AppError("cycle_detected", str(exc), status_code=status.HTTP_422_UNPROCESSABLE_ENTITY) from exc
    except LookupError as exc:
        raise NotFound("concept", payload.target_id) from exc
    await session.commit()
    return {"ok": True}


@router.post("/combine", response_model=ConceptOut, status_code=status.HTTP_201_CREATED)
async def combine_concepts(
    payload: CombineRequest,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """BirdsEyes-style fusion: pick two concepts, generate the idea that
    bridges them, and wire RELATED_TO edges to both parents."""
    from app.modules.brain.schemas import BridgeIdea, ConceptCreate
    from app.modules.users.routes import ensure_profile
    from app.providers.factory import get_llm_provider

    await ensure_profile(session, user.id, user.email)

    a = (await session.execute(select(Concept).where(Concept.id == payload.concept_a))).scalar_one_or_none()
    b = (await session.execute(select(Concept).where(Concept.id == payload.concept_b))).scalar_one_or_none()
    if a is None or b is None:
        raise NotFound("concept", payload.concept_a if a is None else payload.concept_b)

    provider = get_llm_provider()
    response = await provider.generate_structured(
        prompt=(
            f"Two concepts:\n"
            f"1. {a.canonical_name} — {a.description or 'no description'} (domain: {a.domain or 'unknown'})\n"
            f"2. {b.canonical_name} — {b.description or 'no description'} (domain: {b.domain or 'unknown'})\n\n"
            "Propose the single most interesting concept that sits at their intersection — "
            "something a learner excited by both would love to explore. Give it a crisp name, "
            "a two-sentence description, the most fitting domain, and a difficulty 1-5."
        ),
        schema=BridgeIdea,
        system="You are a rigorous, creative intellectual cartographer. Never invent jargon that doesn't exist; name real ideas.",
    )

    session.add(AIGeneration(
        user_id=user.id, feature="concept_combine",
        provider=response.provider, model=response.model,
        input_tokens=response.input_tokens, output_tokens=response.output_tokens,
        latency_ms=response.latency_ms, success=1 if response.structured else 0,
    ))
    if response.structured is None:
        raise AppError("generation_failed", "Model returned unparseable output", status_code=502)

    idea = BridgeIdea.model_validate(response.structured)
    concept, _created = await service.get_or_create_concept(
        session,
        ConceptCreate(
            canonical_name=idea.name,
            description=idea.description or None,
            domain=idea.domain or a.domain or b.domain,
            difficulty=idea.difficulty,
        ),
    )
    await service.ensure_user_concept(session, user.id, concept.id)
    await service.add_edge(session, user.id, concept.id, a.id, EdgeType.RELATED_TO)
    await service.add_edge(session, user.id, concept.id, b.id, EdgeType.RELATED_TO)
    await session.commit()

    return ConceptOut(
        id=concept.id,
        canonical_name=concept.canonical_name,
        description=concept.description,
        domain=concept.domain,
        difficulty=concept.difficulty,
    )

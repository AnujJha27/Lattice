"""Pathway generation: structured LLM output → validated, persisted graph.

Lazy by design (spec §11): only the skeleton is generated — sections,
concepts, prerequisite edges, one-line descriptions. Lessons are generated
on demand in Phase E.

Validation pipeline (spec §38):
    LLM output → Pydantic schema (response_schema) → semantic checks
    (section bounds, concept dedupe) → business rules (DAG) → persistence.
"""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import ConceptEdge, PathwaySection
from app.db.models.concept import EdgeType
from app.db.models.learning import Pathway, PathwayConcept
from app.domain.graph import ensure_acyclic
from app.modules.brain.service import ensure_user_concept, get_or_create_concept
from app.modules.pathways.schemas import GeneratedPathway

logger = logging.getLogger(__name__)

PROMPT_KEY = "pathway_generation"
PROMPT_VERSION = 1

SYSTEM_PROMPT = """You design learning pathways. Given a topic and target depth:
- Decompose the topic into coherent sequential sections (layers).
- Match the requested depth: beginner = 3-4 sections and 6-10 concrete concepts with gentle foundations; intermediate = 4-6 sections and 10-18 concepts with applied techniques; advanced = 6-8 sections and 18-30 concepts including edge cases, proofs, and current frontiers.
- Give every concept one stable, broad domain label (for example, "Formal Verification").
- For every concept, name its prerequisites BY EXACT NAME of other concepts in this pathway.
- Prerequisites must form a DAG — no circular dependencies.
- Descriptions: one clear sentence each. Difficulty 1 (gentle intro) to 5 (advanced).
- Order sections from foundations to advanced material.
Return ONLY JSON matching the requested schema."""


def user_prompt(topic: str, depth: str, known_concepts: list[str]) -> str:
    known = ""
    if known_concepts:
        known_list = ", ".join(known_concepts[:40])
        known = f"\nThe learner already knows: {known_list}. Do not re-teach these; you may reference them as prerequisites."
    return f"Topic: {topic}\nTarget depth: {depth}. Do not under-deliver the depth-specific section and concept range above.{known}"


def validate_generated(raw: GeneratedPathway) -> tuple[GeneratedPathway, int]:
    """Semantic validation. Returns (cleaned, dropped_prerequisite_count)."""
    section_count = len(raw.sections)
    valid_names = {c.name.strip().lower() for c in raw.concepts}
    section_by_name = {c.name.strip().lower(): c.section for c in raw.concepts}

    cleaned_concepts = []
    seen_names: set[str] = set()
    dropped_refs = 0
    for concept in raw.concepts:
        name = concept.name.strip()
        key = name.lower()
        domain = " ".join(concept.domain.split())
        if not name or not domain or key in seen_names or len(valid_names) == 0:
            continue
        seen_names.add(key)
        known_prereqs = [
            p for p in (p.strip() for p in concept.prerequisites)
            if p.lower() in valid_names
            and p.lower() != key
            and section_by_name[p.lower()] < concept.section
        ]
        dropped_refs += len(concept.prerequisites) - len(known_prereqs)
        cleaned_concepts.append(
            concept.model_copy(
                update={
                    "name": name,
                    "domain": domain,
                    "section": min(concept.section, section_count - 1),
                    "prerequisites": known_prereqs,
                }
            )
        )

    # DAG enforcement: greedily accept edges; skip any that would close a cycle.
    accepted_edges: list[tuple[str, str]] = []
    skipped = 0
    id_by_name = {c.name.strip().lower(): f"tmp-{i}" for i, c in enumerate(cleaned_concepts)}
    for concept in cleaned_concepts:
        for prereq in concept.prerequisites:
            src = id_by_name.get(prereq.strip().lower())
            dst = id_by_name.get(concept.name.strip().lower())
            if not src or not dst:
                skipped += 1
                continue
            try:
                ensure_acyclic(set(id_by_name.values()), accepted_edges, (src, dst))
                accepted_edges.append((src, dst))
            except ValueError:
                skipped += 1
                logger.warning("dropped cyclic pathway edge %s -> %s", prereq, concept.name)

    skipped += dropped_refs
    return raw.model_copy(update={"concepts": cleaned_concepts}), skipped


async def persist_pathway(
    session: AsyncSession,
    pathway: Pathway,
    generated: GeneratedPathway,
    skipped_edges: int,
) -> Pathway:
    """Map generated structure onto canonical concepts + edges. Idempotent per run."""
    # Sections
    section_rows = []
    for position, section_spec in enumerate(generated.sections):
        row = PathwaySection(pathway_id=pathway.id, position=position,
                             title=section_spec.title[:200], summary=section_spec.summary[:600])
        session.add(row)
        section_rows.append((row, position))
    await session.flush()

    # Concepts (deduped against canonical store)
    from app.modules.brain.schemas import ConceptCreate

    concept_ids: dict[str, uuid.UUID] = {}
    for order, concept_spec in enumerate(generated.concepts):
        concept, _created = await get_or_create_concept(
            session,
            ConceptCreate(
                canonical_name=concept_spec.name,
                description=concept_spec.description or None,
                domain=concept_spec.domain,
                difficulty=concept_spec.difficulty,
            ),
        )
        await ensure_user_concept(session, pathway.user_id, concept.id)
        concept_ids[concept_spec.name.strip().lower()] = concept.id

        session.add(PathwayConcept(
            pathway_id=pathway.id,
            concept_id=concept.id,
            section_id=section_rows[concept_spec.section][0].id,
            position=order,
        ))

    # Prerequisite edges among pathway concepts (already DAG-checked)
    edge_pairs: list[tuple[uuid.UUID, uuid.UUID]] = []
    tmp_to_id = {}
    for i, concept_spec in enumerate(generated.concepts):
        cid = concept_ids.get(concept_spec.name.strip().lower())
        if cid:
            tmp_to_id[f"tmp-{i}"] = cid
    for concept_spec in generated.concepts:
        dst = concept_ids.get(concept_spec.name.strip().lower())
        for prereq in concept_spec.prerequisites:
            src = concept_ids.get(prereq.strip().lower())
            if not src or not dst or src == dst:
                continue
            try:
                ensure_acyclic(set(map(str, concept_ids.values())),
                               [(str(a), str(b)) for a, b in edge_pairs], (str(src), str(dst)))
                edge_pairs.append((src, dst))
            except ValueError:
                continue

    for src, dst in edge_pairs:
        exists = await session.execute(
            select_existing_edge(src, dst)
        )
        if exists.scalar_one_or_none() is None:
            session.add(ConceptEdge(
                source_id=src, target_id=dst,
                type=EdgeType.PREREQUISITE, created_by=f"ai:{PROMPT_KEY}:{PROMPT_VERSION}",
            ))
    await session.flush()

    # Cross-domain bridges (spec §18 discovery): for the first few pathway
    # concepts, find the nearest existing concept from a *different* domain
    # and wire a RELATED_TO edge when the semantic distance is genuinely close.
    await _bridge_to_other_domains(session, pathway.user_id, concept_ids)

    pathway.generation_metadata = {
        **pathway.generation_metadata,
        "prompt_key": PROMPT_KEY,
        "prompt_version": PROMPT_VERSION,
        "skipped_edges": skipped_edges,
        "model": get_settings().google_api_key_pool and "gemini" or "none",
    }
    return pathway


def select_existing_edge(src, dst):
    from sqlalchemy import select

    from app.db.models import ConceptEdge
    from app.db.models.concept import EdgeType as ET

    return select(ConceptEdge.id).where(
        ConceptEdge.source_id == src, ConceptEdge.target_id == dst, ConceptEdge.type == ET.PREREQUISITE
    )


async def _bridge_to_other_domains(
    session, user_id, concept_ids: dict[str, uuid.UUID], max_bridges: int = 4
) -> int:
    """Embed pathway concepts and connect the closest different-domain neighbour.

    Distance threshold is conservative (< 0.55 cosine) — a bridge must be
    genuinely close or it's noise, not discovery.
    """
    import logging

    from sqlalchemy import select

    from app.db.models import Concept
    from app.providers.embedding import GeminiEmbeddingProvider

    logger = logging.getLogger(__name__)
    items = list(concept_ids.items())[:8]
    if len(items) == 0:
        return 0

    try:
        rows = await session.execute(
            select(Concept).where(Concept.id.in_(concept_ids.values()))
        )
        by_id = {c.id: c for c in rows.scalars().all()}
        texts = []
        targets = []
        for _name, cid in items:
            concept = by_id.get(cid)
            if concept is None:
                continue
            texts.append(f"{concept.canonical_name}. {concept.description or ''}")
            targets.append(concept)

        embedder = GeminiEmbeddingProvider()
        vectors = await embedder.embed(texts)
        # Persist: concept embeddings are the substrate for all future bridges.
        for concept, vector in zip(targets, vectors, strict=True):
            concept.summary_embedding = vector

        # Backfill older concepts that predate embedding, so the neighbour
        # query has a population to search.
        backfill = await session.execute(
            select(Concept)
            .where(Concept.summary_embedding.is_(None))
            .order_by(Concept.created_at.desc())
            .limit(30)
        )
        backfill_concepts = backfill.scalars().all()
        if backfill_concepts:
            backfill_texts = [
                f"{c.canonical_name}. {c.description or ''}" for c in backfill_concepts
            ]
            backfill_vectors = await embedder.embed(backfill_texts)
            for c, v in zip(backfill_concepts, backfill_vectors, strict=True):
                c.summary_embedding = v
        await session.flush()
    except Exception:  # noqa: BLE001 — bridges are enhancement, never fatal
        logger.exception("bridge embedding failed; skipping cross-domain links")
        return 0

    bridges = 0
    for concept, vector in zip(targets, vectors, strict=True):
        if bridges >= max_bridges:
            break
        distance_expr = Concept.summary_embedding.cosine_distance(vector)
        result = await session.execute(
            select(Concept, distance_expr)
            .where(
                Concept.id.notin_(concept_ids.values()),
                Concept.id != concept.id,
                Concept.domain.is_distinct_from(concept.domain),
                Concept.summary_embedding.isnot(None),
            )
            .order_by(distance_expr)
            .limit(1)
        )
        row = result.first()
        if row is None:
            continue
        neighbour, distance = row
        if float(distance) >= 0.35:
            continue
        exists = await session.execute(
            select_existing_edge(concept.id, neighbour.id)
        )
        if exists.scalar_one_or_none() is None:
            session.add(ConceptEdge(
                source_id=concept.id, target_id=neighbour.id,
                type=EdgeType.RELATED_TO, confidence=round(1 - float(distance), 3),
                created_by="ai:domain_bridge:v1",
            ))
            bridges += 1
    return bridges

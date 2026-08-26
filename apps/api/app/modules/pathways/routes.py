"""Pathway routes: create (async generation), list, detail."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import Concept, Pathway, PathwayConcept, PathwaySection, UserConcept
from app.db.models.learning import PathwayStatus
from app.db.session import get_session
from app.modules.pathways.schemas import (
    PathwayConceptOut,
    PathwayCreate,
    PathwayDetail,
    PathwayOut,
    PathwaySectionOut,
)

router = APIRouter(tags=["pathways"])


def _depth_info(metadata: dict) -> tuple[str, str | None]:
    depth = str(metadata.get("target_depth", "beginner"))
    return depth, {"beginner": "intermediate", "intermediate": "advanced"}.get(depth)


@router.post("/pathways", response_model=PathwayOut, status_code=status.HTTP_202_ACCEPTED)
async def create_pathway(
    payload: PathwayCreate,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """Creates a GENERATING pathway; structure arrives via background job."""
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)
    pathway = Pathway(
        user_id=user.id,
        title=payload.topic[:200],
        topic=payload.topic,
        status=PathwayStatus.GENERATING,
        generation_metadata={"target_depth": payload.target_depth},
    )
    session.add(pathway)
    await session.flush()

    from app.jobs.queue import enqueue_job

    await enqueue_job(
        session,
        "PATHWAY_GENERATION",
        {"pathway_id": str(pathway.id), "target_depth": payload.target_depth},
    )
    await session.commit()
    depth, next_depth = _depth_info(pathway.generation_metadata)
    return PathwayOut(
        id=str(pathway.id), title=pathway.title, topic=pathway.topic,
        status=pathway.status.value, created_at=pathway.created_at,
        target_depth=depth, next_depth=next_depth,
    )


@router.get("/pathways", response_model=list[PathwayOut])
async def list_pathways(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    """Single round trip: pathways + aggregated counts via scalar subqueries."""
    concept_count = (
        select(func.count())
        .select_from(PathwayConcept)
        .where(PathwayConcept.pathway_id == Pathway.id)
        .correlate(Pathway)
        .scalar_subquery()
    )
    section_count = (
        select(func.count())
        .select_from(PathwaySection)
        .where(PathwaySection.pathway_id == Pathway.id)
        .correlate(Pathway)
        .scalar_subquery()
    )
    rows = await session.execute(
        select(
            Pathway,
            func.coalesce(concept_count, 0).label("concept_count"),
            func.coalesce(section_count, 0).label("section_count"),
        )
        .where(Pathway.user_id == user.id)
        .order_by(Pathway.created_at.desc())
    )
    return [
        PathwayOut(
            id=str(p.id), title=p.title, topic=p.topic, status=p.status.value,
            created_at=p.created_at,
            section_count=int(section_count_), concept_count=int(concept_count_),
            target_depth=_depth_info(p.generation_metadata)[0], next_depth=_depth_info(p.generation_metadata)[1],
        )
        for p, concept_count_, section_count_ in rows.all()
    ]


@router.delete("/pathways/{pathway_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pathway(
    pathway_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """Delete a pathway. Its sections/links cascade. Concepts that belong to
    this pathway *and* have no life outside it (no edges, no other pathway,
    no lessons) are deleted too — woven-in concepts survive in the Brain."""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import func, select

    from app.db.models import Concept, ConceptEdge, Lesson
    pathway = (await session.execute(
        select(Pathway).where(Pathway.id == pathway_id, Pathway.user_id == user.id)
    )).scalar_one_or_none()
    if pathway is None:
        raise NotFound("pathway", pathway_id)

    concept_ids = [
        row[0] for row in (await session.execute(
            select(PathwayConcept.concept_id).where(PathwayConcept.pathway_id == pathway_id)
        )).all()
    ]

    await session.execute(sa_delete(Pathway).where(Pathway.id == pathway_id))

    # Orphan sweep: concepts only this pathway was holding.
    for concept_id in concept_ids:
        in_other_pathway = (await session.execute(
            select(func.count())
            .select_from(PathwayConcept)
            .where(PathwayConcept.concept_id == concept_id)
        )).scalar() or 0
        edge_count = (await session.execute(
            select(func.count())
            .select_from(ConceptEdge)
            .where((ConceptEdge.source_id == concept_id) | (ConceptEdge.target_id == concept_id))
        )).scalar() or 0
        lesson_count = (await session.execute(
            select(func.count())
            .select_from(Lesson)
            .where(Lesson.concept_id == concept_id)
        )).scalar() or 0

        if in_other_pathway == 0 and edge_count == 0 and lesson_count == 0:
            await session.execute(
                sa_delete(Concept).where(Concept.id == concept_id)
            )

    await session.commit()


@router.get("/pathways/{pathway_id}", response_model=PathwayDetail)
async def get_pathway(
    pathway_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Pathway).where(Pathway.id == pathway_id, Pathway.user_id == user.id)
    )
    pathway = result.scalar_one_or_none()
    if pathway is None:
        raise NotFound("pathway", pathway_id)

    sections_result = await session.execute(
        select(PathwaySection)
        .where(PathwaySection.pathway_id == pathway_id)
        .order_by(PathwaySection.position)
    )
    concepts_result = await session.execute(
        select(PathwayConcept, Concept, UserConcept)
        .join(Concept, Concept.id == PathwayConcept.concept_id)
        .outerjoin(UserConcept, (UserConcept.concept_id == Concept.id) & (UserConcept.user_id == user.id))
        .where(PathwayConcept.pathway_id == pathway_id)
        .order_by(PathwayConcept.position)
    )

    by_section: dict[uuid.UUID, list[PathwayConceptOut]] = {}
    total_concepts = 0
    for link, concept, state in concepts_result.all():
        if link.section_id is None:
            continue
        by_section.setdefault(link.section_id, []).append(PathwayConceptOut(
            concept_id=str(concept.id),
            name=concept.canonical_name,
            description=concept.description,
            difficulty=concept.difficulty,
            mastery_score=float(state.mastery_score) if state else 0.0,
            state=state.state.value if state else "UNSEEN",
            position=link.position,
        ))
        total_concepts += 1

    skipped = int(pathway.generation_metadata.get("skipped_edges", 0))
    depth, next_depth = _depth_info(pathway.generation_metadata)
    return PathwayDetail(
        id=str(pathway.id),
        title=pathway.title,
        topic=pathway.topic,
        description=None,
        status=pathway.status.value,
        created_at=pathway.created_at,
        section_count=len(sections := sections_result.scalars().all()),
        concept_count=total_concepts,
        skipped_edges=skipped,
        target_depth=depth,
        next_depth=next_depth,
        sections=[
            PathwaySectionOut(
                id=str(s.id), position=s.position, title=s.title, summary=s.summary,
                concepts=by_section.get(s.id, []),
            )
            for s in sections
        ],
    )

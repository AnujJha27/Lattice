"""Lesson routes: cached retrieval + grounded generation."""
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import AppError, NotFound
from app.db.models import Concept, Lesson
from app.db.session import get_session
from app.modules.lessons.schemas import LessonContent, LessonOut

router = APIRouter(tags=["lessons"])


def _to_out(lesson: Lesson) -> LessonOut:
    return LessonOut(
        concept_id=str(lesson.concept_id),
        title=lesson.title,
        content=LessonContent.model_validate(lesson.content),
        grounding=lesson.grounding,
        sources=[],  # hydrated below by the caller
        generated_at=lesson.generated_at,
        cached=True,
    )


@router.get("/concepts/{concept_id}/lesson", response_model=LessonOut)
async def get_lesson(
    concept_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    """Return the cached lesson for this concept, or 404 if none exists yet."""
    result = await session.execute(
        select(Lesson)
        .where(Lesson.concept_id == concept_id, Lesson.user_id == user.id)
        .order_by(Lesson.created_at.desc())
        .limit(1)
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise NotFound("lesson", concept_id)

    out = _to_out(lesson)

    # Hydrate the source contexts used during generation.
    from sqlalchemy import text as sql_text

    rows = await session.execute(
        sql_text(
            """
            SELECT s.id, s.title, s.publisher, s.publication_date, s.authors, s.url
            FROM lesson_sources ls JOIN sources s ON s.id = ls.source_id
            WHERE ls.lesson_id = :lid ORDER BY ls.relevance DESC
            """
        ),
        {"lid": str(lesson.id)},
    )
    from app.modules.lessons.context import gather_contexts  # noqa: F401
    from app.modules.lessons.schemas import SourceContext

    out.sources = [
        SourceContext(
            index=i,
            source_id=str(row.id),
            title=row.title,
            publisher=row.publisher,
            year=row.publication_date.year if row.publication_date else None,
            authors=list(row.authors or [])[:5],
            url=row.url,
            excerpt="(saved with the lesson)",
            from_snippet=False,
        )
        for i, row in enumerate(rows.all())
    ]
    return out


@router.post("/concepts/{concept_id}/lesson", status_code=status.HTTP_202_ACCEPTED)
async def generate_concept_lesson(
    concept_id: uuid.UUID,
    user: CurrentUser = CurrentUserDep,
    depth: str = "beginner",
    session: AsyncSession = Depends(get_session),
):
    """Queue book-chapter lesson generation. Poll GET /lesson until it appears."""
    if depth not in ("beginner", "intermediate", "advanced"):
        raise AppError("invalid_depth", "depth must be beginner|intermediate|advanced")

    from app.jobs.queue import enqueue_job
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)

    result = await session.execute(select(Concept).where(Concept.id == concept_id))
    concept = result.scalar_one_or_none()
    if concept is None:
        raise NotFound("concept", concept_id)

    await enqueue_job(
        session,
        "LESSON_GENERATION",
        {"concept_id": str(concept_id), "user_id": str(user.id), "depth": depth},
        dedupe_key=f"lesson:{user.id}:{concept_id}",
    )
    await session.commit()
    return {"status": "generating", "concept_id": str(concept_id)}

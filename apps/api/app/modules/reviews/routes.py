"""Deterministic spaced-review queue backed by existing user_concepts state."""
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import Concept, Review, UserConcept
from app.db.models.learning import MasteryState
from app.db.session import get_session
from app.modules.reviews.service import apply_review, mark_review_due

router = APIRouter(tags=["reviews"])


class ReviewSubmit(BaseModel):
    correct: bool
    confidence: int = Field(default=3, ge=1, le=5)


class ScheduleRequest(BaseModel):
    concept_id: UUID


class ReviewItem(BaseModel):
    concept_id: UUID
    name: str
    mastery_score: float
    state: str
    next_review_at: datetime | None


@router.get("/reviews/due", response_model=list[ReviewItem])
async def due_reviews(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Concept, UserConcept)
        .join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id, UserConcept.next_review_at <= datetime.now(UTC))
        .order_by(UserConcept.next_review_at)
        .limit(20)
    )
    items = []
    changed = False
    for concept, state in rows.all():
        changed = mark_review_due(state) or changed
        items.append(ReviewItem(
            concept_id=concept.id, name=concept.canonical_name,
            mastery_score=float(state.mastery_score), state=state.state.value,
            next_review_at=state.next_review_at,
        ))
    if changed:
        await session.commit()
    return items


@router.post("/reviews/schedule", response_model=ReviewItem)
async def schedule_review(payload: ScheduleRequest, user: CurrentUser = CurrentUserDep,
                          session: AsyncSession = Depends(get_session)):
    row = (await session.execute(select(Concept, UserConcept).join(UserConcept, UserConcept.concept_id == Concept.id).where(UserConcept.user_id == user.id, UserConcept.concept_id == payload.concept_id))).one_or_none()
    if row is None:
        raise NotFound("concept", payload.concept_id)
    concept, state = row
    state.next_review_at = datetime.now(UTC)
    state.state = MasteryState.REVIEW_DUE
    await session.commit()
    return ReviewItem(concept_id=concept.id, name=concept.canonical_name,
                      mastery_score=float(state.mastery_score), state=state.state.value,
                      next_review_at=state.next_review_at)


@router.post("/concepts/{concept_id}/reviews", response_model=ReviewItem)
async def submit_review(concept_id: UUID, payload: ReviewSubmit, user: CurrentUser = CurrentUserDep,
                        session: AsyncSession = Depends(get_session)):
    row = (await session.execute(
        select(Concept, UserConcept)
        .join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id, UserConcept.concept_id == concept_id)
    )).one_or_none()
    if row is None:
        raise NotFound("concept", concept_id)
    concept, state = row
    previous_mastery = apply_review(state, correct=payload.correct, confidence=payload.confidence)
    session.add(Review(
        user_id=user.id,
        concept_id=concept_id,
        correct=payload.correct,
        confidence=payload.confidence,
        previous_mastery=previous_mastery,
        mastery_after=float(state.mastery_score),
    ))
    await session.commit()
    return ReviewItem(concept_id=concept.id, name=concept.canonical_name,
                      mastery_score=float(state.mastery_score), state=state.state.value,
                      next_review_at=state.next_review_at)

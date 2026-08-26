"""Deterministic spaced-review queue backed by existing user_concepts state."""
from datetime import UTC, datetime, timedelta
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
    next_review_at: datetime | None


def mastery_state(score: float) -> MasteryState:
    if score >= 85:
        return MasteryState.MASTERED
    if score >= 60:
        return MasteryState.FAMILIAR
    if score > 0:
        return MasteryState.LEARNING
    return MasteryState.UNSEEN


@router.get("/reviews/due", response_model=list[ReviewItem])
async def due_reviews(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Concept, UserConcept)
        .join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id, UserConcept.next_review_at <= datetime.now(UTC))
        .order_by(UserConcept.next_review_at)
        .limit(20)
    )
    return [ReviewItem(concept_id=concept.id, name=concept.canonical_name,
                       mastery_score=float(state.mastery_score), next_review_at=state.next_review_at)
            for concept, state in rows.all()]


@router.post("/reviews/schedule", response_model=ReviewItem)
async def schedule_review(payload: ScheduleRequest, user: CurrentUser = CurrentUserDep,
                          session: AsyncSession = Depends(get_session)):
    row = (await session.execute(select(Concept, UserConcept).join(UserConcept, UserConcept.concept_id == Concept.id).where(UserConcept.user_id == user.id, UserConcept.concept_id == payload.concept_id))).one_or_none()
    if row is None:
        raise NotFound("concept", payload.concept_id)
    concept, state = row
    state.next_review_at = datetime.now(UTC)
    await session.commit()
    return ReviewItem(concept_id=concept.id, name=concept.canonical_name, mastery_score=float(state.mastery_score), next_review_at=state.next_review_at)


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
    state.review_count += 1
    state.attempt_count += 1
    state.confidence = payload.confidence * 20
    state.mastery_score = max(0, min(100, float(state.mastery_score) + (12 if payload.correct else -8)))
    if payload.correct:
        state.successful_reviews += 1
    else:
        state.successful_reviews = 0
    state.state = mastery_state(float(state.mastery_score))
    state.last_tested_at = datetime.now(UTC)
    if payload.correct:
        interval_days = min(
            60,
            max(
                1,
                round(
                    (1 + payload.confidence)
                    * (1 + float(state.mastery_score) / 100)
                    * (1 + state.successful_reviews * 0.35)
                ),
            ),
        )
    else:
        interval_days = 1
    state.next_review_at = datetime.now(UTC) + timedelta(days=interval_days)
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
                      mastery_score=float(state.mastery_score), next_review_at=state.next_review_at)

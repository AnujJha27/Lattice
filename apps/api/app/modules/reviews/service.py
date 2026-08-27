"""Shared deterministic mastery transition for quiz and review submissions."""
from datetime import UTC, datetime, timedelta

from app.db.models.learning import MasteryState, UserConcept


def apply_review(
    state: UserConcept,
    *,
    correct: bool,
    confidence: int,
    now: datetime | None = None,
) -> float:
    """Apply one review and return the mastery score from before the attempt."""
    now = now or datetime.now(UTC)
    previous_mastery = float(state.mastery_score)
    state.review_count += 1
    state.attempt_count += 1
    state.confidence = confidence * 20
    state.mastery_score = max(0, min(100, previous_mastery + (12 if correct else -8)))
    state.successful_reviews = state.successful_reviews + 1 if correct else 0
    state.state = (
        MasteryState.MASTERED
        if state.mastery_score >= 85
        else MasteryState.FAMILIAR
        if state.mastery_score >= 60
        else MasteryState.LEARNING
    )
    state.last_tested_at = now
    interval_days = 1
    if correct:
        interval_days = min(
            60,
            max(
                1,
                round(
                    (1 + confidence)
                    * (1 + state.mastery_score / 100)
                    * (1 + state.successful_reviews * 0.35)
                ),
            ),
        )
    state.next_review_at = now + timedelta(days=interval_days)
    return previous_mastery


def mark_review_due(state: UserConcept, now: datetime | None = None) -> bool:
    """Mark an elapsed scheduled review without changing mastery."""
    if state.next_review_at is None:
        return False
    now = now or datetime.now(UTC)
    due_at = state.next_review_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    if due_at > now or state.state == MasteryState.REVIEW_DUE:
        return False
    state.state = MasteryState.REVIEW_DUE
    return True

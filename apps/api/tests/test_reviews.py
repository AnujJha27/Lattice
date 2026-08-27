from datetime import UTC, datetime

from app.db.models.learning import MasteryState, UserConcept
from app.modules.reviews.service import apply_review


def test_apply_review_updates_mastery_and_schedule():
    state = UserConcept(
        mastery_score=50,
        state=MasteryState.LEARNING,
        confidence=0,
        attempt_count=2,
        successful_reviews=1,
        review_count=1,
    )
    now = datetime(2026, 8, 27, tzinfo=UTC)

    previous = apply_review(state, correct=True, confidence=4, now=now)

    assert previous == 50
    assert state.mastery_score == 62
    assert state.state == MasteryState.FAMILIAR
    assert state.successful_reviews == 2
    assert state.confidence == 80
    assert state.next_review_at == datetime(2026, 9, 10, tzinfo=UTC)


def test_review_due_state_is_cleared_after_a_missed_review():
    state = UserConcept(
        mastery_score=70,
        state=MasteryState.REVIEW_DUE,
        confidence=60,
        attempt_count=3,
        successful_reviews=2,
        review_count=3,
    )

    apply_review(state, correct=False, confidence=2, now=datetime(2026, 8, 27, tzinfo=UTC))

    assert state.mastery_score == 62
    assert state.state == MasteryState.FAMILIAR


def test_mark_review_due_only_changes_elapsed_schedules():
    from app.modules.reviews.service import mark_review_due

    now = datetime(2026, 8, 27, tzinfo=UTC)
    state = UserConcept(
        state=MasteryState.FAMILIAR,
        next_review_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert mark_review_due(state, now) is True
    assert state.state == MasteryState.REVIEW_DUE
    assert mark_review_due(state, now) is False

    future = UserConcept(
        state=MasteryState.FAMILIAR,
        next_review_at=datetime(2026, 8, 28, tzinfo=UTC),
    )
    assert mark_review_due(future, now) is False

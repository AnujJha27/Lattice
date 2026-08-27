from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from app.modules.recommendations.routes import (
    clicked_mastery_delta,
    recommendation_reason,
    recommendation_score,
)


def test_recommendation_reason_prefers_due_review():
    now = datetime.now(UTC)
    assert recommendation_reason(80, 20, True, now - timedelta(days=1), now) == "Due for review"


def test_recommendation_reason_explains_prerequisites_and_mastery():
    now = datetime.now(UTC)
    assert recommendation_reason(20, 80, True, None, now) == "Prerequisites are ready"
    assert recommendation_reason(20, 80, False, None, now) == "Interest is ahead of mastery"
    assert recommendation_reason(20, 20, False, None, now) == "Strengthen your foundation"


def test_recommendation_score_rewards_goal_readiness_and_recency():
    focused, factors = recommendation_score(1, 0.8, 1, 0.8, 0.5, 0.2)
    neglected, _ = recommendation_score(0, 0.2, 0, 0.1, 0, 0.9)

    assert focused > neglected
    assert factors == {
        "goal": 1.0,
        "interest": 0.8,
        "prerequisite_ready": 1.0,
        "recency": 0.8,
        "neighborhood": 0.5,
        "mastery": 0.2,
    }


def test_clicked_mastery_delta_excludes_reviews_before_the_click():
    concept_id = uuid4()
    click_at = datetime(2026, 8, 28, 10, tzinfo=UTC)
    clicks = [SimpleNamespace(concept_id=concept_id, created_at=click_at)]
    reviews = [
        SimpleNamespace(
            concept_id=concept_id,
            created_at=click_at - timedelta(minutes=1),
            previous_mastery=20,
            mastery_after=80,
        ),
        SimpleNamespace(
            concept_id=concept_id,
            created_at=click_at + timedelta(minutes=1),
            previous_mastery=20,
            mastery_after=32,
        ),
    ]

    assert clicked_mastery_delta(clicks, reviews) == 12

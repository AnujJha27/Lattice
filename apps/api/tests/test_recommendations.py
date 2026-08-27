from datetime import UTC, datetime, timedelta

from app.modules.recommendations.routes import recommendation_reason


def test_recommendation_reason_prefers_due_review():
    now = datetime.now(UTC)
    assert recommendation_reason(80, 20, True, now - timedelta(days=1), now) == "Due for review"


def test_recommendation_reason_explains_prerequisites_and_mastery():
    now = datetime.now(UTC)
    assert recommendation_reason(20, 80, True, None, now) == "Prerequisites are ready"
    assert recommendation_reason(20, 80, False, None, now) == "Interest is ahead of mastery"
    assert recommendation_reason(20, 20, False, None, now) == "Strengthen your foundation"

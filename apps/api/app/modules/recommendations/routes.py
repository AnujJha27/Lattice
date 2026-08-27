"""Deterministic, explainable recommendations with measurable outcomes."""
import math
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import (
    Concept,
    ConceptEdge,
    Goal,
    GoalConcept,
    RecommendationEvent,
    Review,
    UserConcept,
)
from app.db.models.concept import EdgeType
from app.db.models.learning import GoalStatus
from app.db.models.recommendation import RecommendationEventType
from app.db.session import get_session

router = APIRouter(tags=["recommendations"])


class Recommendation(BaseModel):
    concept_id: str
    name: str
    score: float
    reason: str
    factors: dict[str, float] = Field(default_factory=dict)


class RecommendationClick(BaseModel):
    score: float = 0
    factors: dict[str, float] = Field(default_factory=dict)


class RecommendationEvaluation(BaseModel):
    window_days: int
    impressions: int
    clicks: int
    ctr: float
    clicked_mastery_delta: float


def _recency_score(state: UserConcept, now: datetime) -> float:
    timestamps = [value for value in (state.last_seen_at, state.last_tested_at) if value is not None]
    if not timestamps:
        return 0.0
    last_activity = max(timestamps)
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=UTC)
    return max(0.0, min(1.0, math.exp(-max(0.0, (now - last_activity).total_seconds()) / 2_592_000)))


def recommendation_score(
    goal: float,
    interest: float,
    prerequisite_ready: float,
    recency: float,
    neighborhood: float,
    mastery: float,
) -> tuple[float, dict[str, float]]:
    """Rank with facts computed by the API; the LLM never changes this order."""
    factors = {
        "goal": round(max(0.0, min(1.0, goal)), 3),
        "interest": round(max(0.0, min(1.0, interest)), 3),
        "prerequisite_ready": round(max(0.0, min(1.0, prerequisite_ready)), 3),
        "recency": round(max(0.0, min(1.0, recency)), 3),
        "neighborhood": round(max(0.0, min(1.0, neighborhood)), 3),
        "mastery": round(max(0.0, min(1.0, mastery)), 3),
    }
    score = (
        0.30 * factors["goal"]
        + 0.25 * factors["interest"]
        + 0.20 * factors["prerequisite_ready"]
        + 0.15 * factors["recency"]
        + 0.10 * factors["neighborhood"]
        - 0.20 * factors["mastery"]
    )
    return round(max(0.0, score), 3), factors


def recommendation_reason(
    mastery_score: float,
    interest_score: float,
    prerequisites_ready: bool,
    next_review_at: datetime | None,
    now: datetime,
) -> str:
    if next_review_at and next_review_at <= now:
        return "Due for review"
    if prerequisites_ready:
        return "Prerequisites are ready"
    if interest_score >= 60 and interest_score >= mastery_score + 15:
        return "Interest is ahead of mastery"
    if mastery_score < 60:
        return "Strengthen your foundation"
    return "A strong next step"


def clicked_mastery_delta(clicks: list[RecommendationEvent], reviews: list[Review]) -> float:
    """Measure mastery change only after the first click for each concept."""
    first_click_at = {}
    for click in clicks:
        if click.created_at is None:
            continue
        previous = first_click_at.get(click.concept_id)
        if previous is None or click.created_at < previous:
            first_click_at[click.concept_id] = click.created_at
    return sum(
        float(review.mastery_after) - float(review.previous_mastery)
        for review in reviews
        if review.concept_id in first_click_at
        and review.created_at is not None
        and review.created_at >= first_click_at[review.concept_id]
    )


@router.get("/recommendations", response_model=list[Recommendation])
async def recommendations(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Concept, UserConcept).join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id).order_by(UserConcept.mastery_score, UserConcept.interest_score.desc()).limit(30)
    )
    candidates = rows.all()
    if not candidates:
        return []
    candidate_ids = [concept.id for concept, _ in candidates]
    states = {concept.id: state for concept, state in candidates}
    goals = await session.execute(
        select(GoalConcept.concept_id, GoalConcept.importance)
        .join(Goal, Goal.id == GoalConcept.goal_id)
        .where(Goal.user_id == user.id, Goal.status == GoalStatus.ACTIVE, GoalConcept.concept_id.in_(candidate_ids))
    )
    goal_relevance = {concept_id: float(importance) for concept_id, importance in goals.all()}
    prereq_rows = await session.execute(select(ConceptEdge).where(
        ConceptEdge.type == EdgeType.PREREQUISITE, ConceptEdge.target_id.in_(candidate_ids)
    ))
    prereqs: dict[UUID, set[UUID]] = {}
    for edge in prereq_rows.scalars().all():
        prereqs.setdefault(edge.target_id, set()).add(edge.source_id)
    ready = [(concept, state) for concept, state in candidates if all(
        source_id in states and float(states[source_id].mastery_score) >= 60
        for source_id in prereqs.get(concept.id, set())
    )]
    candidates = ready or candidates
    now = datetime.now(UTC)
    ready_ids = {concept.id for concept, _ in ready}
    neighbors: dict[UUID, set[UUID]] = {concept_id: set() for concept_id in candidate_ids}
    edge_rows = await session.execute(select(ConceptEdge).where(
        ConceptEdge.source_id.in_(candidate_ids), ConceptEdge.target_id.in_(candidate_ids)
    ))
    for edge in edge_rows.scalars().all():
        neighbors[edge.source_id].add(edge.target_id)
        neighbors[edge.target_id].add(edge.source_id)
    ranked = []
    for concept, state in candidates:
        score, factors = recommendation_score(
            goal_relevance.get(concept.id, 0),
            float(state.interest_score) / 100,
            float(concept.id in ready_ids),
            _recency_score(state, now),
            min(1.0, len(neighbors[concept.id]) / 6),
            float(state.mastery_score) / 100,
        )
        ranked.append(Recommendation(
            concept_id=str(concept.id), name=concept.canonical_name, score=score,
            reason=recommendation_reason(
                float(state.mastery_score), float(state.interest_score),
                bool(prereqs.get(concept.id)) and concept.id in ready_ids,
                state.next_review_at, now,
            ),
            factors=factors,
        ))
    ranked.sort(key=lambda item: item.score, reverse=True)
    concepts_by_id = {str(concept.id): concept for concept, _ in candidates}
    selected: list[Recommendation] = []
    domain_counts: dict[str, int] = {}
    for item in ranked:
        domain = concepts_by_id[item.concept_id].domain or "Uncategorized"
        if domain_counts.get(domain, 0) >= 2:
            continue
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        selected.append(item)
        if len(selected) == 5:
            break
    for item in selected:
        session.add(RecommendationEvent(user_id=user.id, concept_id=UUID(item.concept_id),
                                         event_type=RecommendationEventType.IMPRESSION,
                                         score=item.score, factors=item.factors))
    await session.commit()
    return selected


@router.post("/recommendations/{concept_id}/click")
async def recommendation_click(concept_id: str, payload: RecommendationClick = RecommendationClick(),
                               user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    try:
        concept_uuid = UUID(concept_id)
    except ValueError:
        raise NotFound("concept", concept_id) from None
    exists = await session.scalar(select(UserConcept.concept_id).where(UserConcept.user_id == user.id, UserConcept.concept_id == concept_uuid))
    if exists is None:
        raise NotFound("concept", concept_id)
    session.add(RecommendationEvent(user_id=user.id, concept_id=concept_uuid,
                                     event_type=RecommendationEventType.CLICK,
                                     score=payload.score, factors=payload.factors))
    await session.commit()
    return {"ok": True}


@router.get("/recommendations/evaluation", response_model=RecommendationEvaluation)
async def recommendation_evaluation(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    since = datetime.now(UTC) - timedelta(days=30)
    events = (await session.execute(select(RecommendationEvent).where(
        RecommendationEvent.user_id == user.id, RecommendationEvent.created_at >= since
    ))).scalars().all()
    clicks = [event for event in events if event.event_type == RecommendationEventType.CLICK]
    reviews = (await session.execute(select(Review).where(
        Review.user_id == user.id, Review.created_at >= since
    ))).scalars().all()
    delta = clicked_mastery_delta(clicks, reviews)
    impressions = sum(event.event_type == RecommendationEventType.IMPRESSION for event in events)
    return RecommendationEvaluation(window_days=30, impressions=impressions, clicks=len(clicks),
                                     ctr=round(len(clicks) / impressions, 3) if impressions else 0,
                                     clicked_mastery_delta=round(delta, 2))

"""Explainable hybrid recommendations with measurable outcomes."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import NotFound
from app.db.models import Concept, ConceptEdge, RecommendationEvent, Review, UserConcept
from app.db.models.concept import EdgeType
from app.db.models.recommendation import RecommendationEventType
from app.db.session import get_session

router = APIRouter(tags=["recommendations"])


class Recommendation(BaseModel):
    concept_id: str
    name: str
    score: float
    factors: dict[str, float] = Field(default_factory=dict)


class RankingScores(BaseModel):
    scores: dict[str, float] = Field(default_factory=dict)


class RecommendationClick(BaseModel):
    score: float = 0
    factors: dict[str, float] = Field(default_factory=dict)


class RecommendationEvaluation(BaseModel):
    window_days: int
    impressions: int
    clicks: int
    ctr: float
    clicked_mastery_delta: float


async def llm_scores(candidates: list[tuple[Concept, UserConcept]]) -> dict[str, float]:
    """Gemini is intentionally isolated from the OpenRouter generation pool."""
    from app.core.config import get_settings
    from app.providers.gemini import GeminiProvider

    if not get_settings().google_api_key:
        return {}
    prompt = "Score each candidate 0..1 for what this learner should study next. Return ids only:\n" + "\n".join(
        f"{concept.id}: {concept.canonical_name} (mastery {float(state.mastery_score):.0f}, interest {float(state.interest_score):.0f})"
        for concept, state in candidates
    )
    response = await GeminiProvider().generate_structured(prompt, RankingScores)
    return RankingScores.model_validate(response.structured or {}).scores


def _deterministic_score(state: UserConcept, now: datetime) -> float:
    due = 20 if state.next_review_at and state.next_review_at <= now else 0
    return 0.45 * float(state.interest_score) + 0.3 * (100 - float(state.mastery_score)) + due


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
    try:
        scores = await llm_scores(candidates)
    except Exception:
        scores = {}
    now = datetime.now(UTC)
    ready_ids = {concept.id for concept, _ in ready}
    ranked = [Recommendation(
        concept_id=str(concept.id), name=concept.canonical_name,
        score=round((deterministic := _deterministic_score(state, now)) + 30 * (llm := max(0, min(1, scores.get(str(concept.id), 0)))), 2),
        factors={"deterministic": round(deterministic, 2), "llm": round(llm, 3),
                 "prerequisite_ready": 1.0 if concept.id in ready_ids else 0.0},
    ) for concept, state in candidates]
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
    delta = sum(float(review.mastery_after) - float(review.previous_mastery)
                for review in reviews if any(review.concept_id == click.concept_id for click in clicks))
    impressions = sum(event.event_type == RecommendationEventType.IMPRESSION for event in events)
    return RecommendationEvaluation(window_days=30, impressions=impressions, clicks=len(clicks),
                                     ctr=round(len(clicks) / impressions, 3) if impressions else 0,
                                     clicked_mastery_delta=round(delta, 2))

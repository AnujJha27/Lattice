"""Small, explainable discovery view derived from the user's graph and reviews."""
from datetime import UTC, datetime, timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.db.models import Concept, ConceptEdge, PortraitFeedback, PortraitSnapshot, Review, UserConcept
from app.db.models.portrait import PortraitFeedbackKind
from app.db.models.concept import EdgeType
from app.db.session import get_session

router = APIRouter(tags=["discovery"])


class PortraitItem(BaseModel):
    concept_id: str | None = None
    name: str
    domain: str
    score: float = 0
    reason: str


class Portrait(BaseModel):
    bridges: list[PortraitItem]
    gaps: list[PortraitItem]
    emerging_interests: list[PortraitItem]
    adjacent_fields: list[str]
    evolution: dict[str, float]


class PortraitHistoryItem(BaseModel):
    created_at: datetime
    evolution: dict[str, float]


class PortraitFeedbackIn(BaseModel):
    kind: str
    subject: str = Field(min_length=1, max_length=500)
    accepted: bool


@router.get("/discovery/portrait", response_model=Portrait)
async def portrait(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    states = (await session.execute(
        select(Concept, UserConcept).join(UserConcept, UserConcept.concept_id == Concept.id)
        .where(UserConcept.user_id == user.id)
    )).all()
    concepts = {concept.id: (concept, state) for concept, state in states}
    if not concepts:
        return Portrait(bridges=[], gaps=[], emerging_interests=[], adjacent_fields=[], evolution={"concepts": 0, "mastered": 0, "reviews": 0, "recent_reviews": 0, "mastery_delta": 0})

    ids = list(concepts)
    edges = (await session.execute(select(ConceptEdge).where(
        ConceptEdge.type.in_([EdgeType.RELATED_TO, EdgeType.PREREQUISITE]),
        or_(ConceptEdge.source_id.in_(ids), ConceptEdge.target_id.in_(ids)),
    ))).scalars().all()
    bridges: list[PortraitItem] = []
    adjacent: set[str] = set()
    for edge in edges:
        if edge.source_id not in concepts or edge.target_id not in concepts:
            continue
        left, right = concepts[edge.source_id][0], concepts[edge.target_id][0]
        left_domain, right_domain = left.domain or "Uncategorized", right.domain or "Uncategorized"
        if left_domain != right_domain:
            adjacent.update((left_domain, right_domain))
            bridges.append(PortraitItem(
                concept_id=str(right.id), name=f"{left.canonical_name} ↔ {right.canonical_name}",
                domain=f"{left_domain} · {right_domain}", score=round(float(edge.confidence or 0.5), 2),
                reason="Cross-domain connection in your Brain",
            ))

    gaps = [PortraitItem(concept_id=str(c.id), name=c.canonical_name, domain=c.domain or "Uncategorized",
                         score=round(float(s.mastery_score), 1), reason="Low mastery on a connected concept")
            for c, s in sorted((v for v in concepts.values()), key=lambda pair: float(pair[1].mastery_score))[:8]
            if float(s.mastery_score) < 60]
    emerging = [PortraitItem(concept_id=str(c.id), name=c.canonical_name, domain=c.domain or "Uncategorized",
                             score=round(float(s.interest_score), 1), reason="High interest, still being learned")
                for c, s in sorted((v for v in concepts.values()), key=lambda pair: float(pair[1].interest_score), reverse=True)[:8]
                if float(s.interest_score) > 0 and float(s.mastery_score) < 85]
    mastered = sum(float(s.mastery_score) >= 85 for _, s in concepts.values())
    reviews = sum(int(s.review_count or 0) for _, s in concepts.values())
    recent = (await session.execute(select(Review).where(Review.user_id == user.id).order_by(Review.created_at.desc()).limit(100))).scalars().all()
    recent_reviews = [r for r in recent if r.created_at and (datetime.now(UTC) - r.created_at).days <= 30]
    result = Portrait(bridges=bridges[:8], gaps=gaps, emerging_interests=emerging,
                      adjacent_fields=sorted(adjacent),
                      evolution={"concepts": len(concepts), "mastered": mastered, "reviews": reviews,
                                 "recent_reviews": len(recent_reviews),
                                 "mastery_delta": round(sum(float(r.mastery_after) - float(r.previous_mastery) for r in recent_reviews), 1)})
    latest = (await session.execute(select(PortraitSnapshot).where(PortraitSnapshot.user_id == user.id)
                                    .order_by(PortraitSnapshot.created_at.desc()).limit(1))).scalar_one_or_none()
    if latest is None or not latest.created_at or (datetime.now(UTC) - latest.created_at) >= timedelta(hours=24):
        session.add(PortraitSnapshot(user_id=user.id, payload=result.model_dump(mode="json")))
        await session.commit()
    return result


@router.get("/discovery/portrait/history", response_model=list[PortraitHistoryItem])
async def portrait_history(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(PortraitSnapshot).where(PortraitSnapshot.user_id == user.id)
                                 .order_by(PortraitSnapshot.created_at.desc()).limit(30))
    return [PortraitHistoryItem(created_at=row.created_at, evolution=row.payload.get("evolution", {}))
            for row in rows.scalars().all()]


@router.post("/discovery/portrait/feedback")
async def portrait_feedback(payload: PortraitFeedbackIn, user: CurrentUser = CurrentUserDep,
                            session: AsyncSession = Depends(get_session)):
    try:
        kind = PortraitFeedbackKind(payload.kind)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="kind must be BRIDGE, GAP, or EMERGING_INTEREST") from None
    session.add(PortraitFeedback(user_id=user.id, kind=kind, subject=payload.subject, accepted=payload.accepted))
    await session.commit()
    return {"ok": True}

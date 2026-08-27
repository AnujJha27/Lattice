"""Discovery compatibility routes and learner corrections."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.db.models import PortraitFeedback
from app.db.models.portrait import PortraitFeedbackKind
from app.db.session import get_session
from app.modules.portrait.schemas import PortraitModel
from app.modules.portrait.service import get_portrait, get_portrait_history

router = APIRouter(tags=["discovery"])


class PortraitFeedbackIn(BaseModel):
    kind: str
    subject: str = Field(min_length=1, max_length=500)
    accepted: bool


@router.get("/discovery/portrait", response_model=PortraitModel)
async def portrait(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)) -> PortraitModel:
    return await get_portrait(session, user, recompute=False)


@router.get("/discovery/portrait/history", response_model=list[PortraitModel])
async def portrait_history(user: CurrentUser = CurrentUserDep, session: AsyncSession = Depends(get_session)) -> list[PortraitModel]:
    return await get_portrait_history(session, user)


@router.post("/discovery/portrait/feedback")
async def portrait_feedback(payload: PortraitFeedbackIn, user: CurrentUser = CurrentUserDep,
                            session: AsyncSession = Depends(get_session)):
    try:
        kind = PortraitFeedbackKind(payload.kind)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="kind must be BRIDGE, GAP, or EMERGING_INTEREST") from None
    from app.modules.users.routes import ensure_profile

    await ensure_profile(session, user.id, user.email)
    session.add(PortraitFeedback(user_id=user.id, kind=kind, subject=payload.subject, accepted=payload.accepted))
    await session.commit()
    return {"ok": True}

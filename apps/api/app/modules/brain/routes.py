"""Brain graph endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.db.session import get_session
from app.modules.brain.schemas import BrainGraphResponse
from app.modules.brain.service import get_brain_graph

router = APIRouter(tags=["brain"])


@router.get("/brain/graph", response_model=BrainGraphResponse)
async def brain_graph(
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> BrainGraphResponse:
    """The user's full Brain: concepts they've engaged with + connecting edges."""
    return await get_brain_graph(session, user)

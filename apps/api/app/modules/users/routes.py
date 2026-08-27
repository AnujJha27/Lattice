"""Users module: profile mirror + ensure_profile helper."""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.db.models import Profile
from app.db.session import get_session

router = APIRouter(prefix="/users", tags=["users"])


async def ensure_profile(session: AsyncSession, user_id: uuid.UUID, email: str | None = None) -> Profile:
    """Idempotently create the profile row mirroring auth.users."""
    result = await session.execute(select(Profile).where(Profile.id == user_id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(id=user_id, display_name=email.split("@")[0] if email else None)
        session.add(profile)
        await session.flush()
    return profile


class ProfileOut(BaseModel):
    id: uuid.UUID
    display_name: str | None
    onboarded: bool


@router.get("/me", response_model=ProfileOut)
async def read_me(
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
):
    profile = await ensure_profile(session, user.id, user.email)
    return ProfileOut(
        id=profile.id,
        display_name=profile.display_name,
        onboarded=profile.onboarded_at is not None,
    )


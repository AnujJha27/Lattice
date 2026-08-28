"""Users module: profile mirror + ensure_profile helper."""
import logging
import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile
from httpx import HTTPError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, CurrentUserDep
from app.core.errors import AppError, NotFound
from app.db.models import PortraitEvent, Profile
from app.db.models.portrait import PortraitEventType
from app.db.session import get_session
from app.providers.storage import make_storage

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)
MAX_PORTRAIT_PHOTO_BYTES = 8 * 1024 * 1024
PHOTO_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}


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
    portrait_photo_enabled: bool
    has_portrait_photo: bool


class PortraitPhotoOut(BaseModel):
    enabled: bool
    has_photo: bool


class PortraitPhotoSettingsIn(BaseModel):
    enabled: bool


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
        portrait_photo_enabled=bool(profile.portrait_photo_enabled),
        has_portrait_photo=profile.portrait_photo_key is not None,
    )


async def _profile_for_user(session: AsyncSession, user: CurrentUser) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.id == user.id))
    return profile or await ensure_profile(session, user.id, user.email)


def _photo_format(file: UploadFile, data: bytes) -> tuple[str, str] | None:
    content_type = file.content_type or ""
    extension = PHOTO_TYPES.get(content_type)
    if extension is None:
        filename = (file.filename or "").lower()
        extension = next((value for value in PHOTO_TYPES.values() if filename.endswith(f".{value}")), None)
    signatures = {
        "jpg": data.startswith(b"\xff\xd8\xff"),
        "png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    return (extension, f"image/{'jpeg' if extension == 'jpg' else extension}") if extension and signatures.get(extension) else None


@router.post("/me/portrait-photo", response_model=PortraitPhotoOut)
async def upload_portrait_photo(
    file: UploadFile = File(...),
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> PortraitPhotoOut:
    data = await file.read(MAX_PORTRAIT_PHOTO_BYTES + 1)
    photo = _photo_format(file, data)
    if len(data) > MAX_PORTRAIT_PHOTO_BYTES or photo is None:
        raise AppError("invalid_portrait_photo", "Use a JPEG, PNG, or WebP image up to 8 MB")
    profile = await _profile_for_user(session, user)
    key = f"portrait-photos/{user.id}.{photo[0]}"
    try:
        await make_storage().put(key, data, photo[1])
    except (HTTPError, OSError, RuntimeError) as exc:
        raise AppError("portrait_photo_unavailable", "Portrait photo storage is unavailable", 503) from exc
    old_key = profile.portrait_photo_key
    was_enabled = bool(profile.portrait_photo_enabled)
    profile.portrait_photo_key = key
    profile.portrait_photo_content_type = photo[1]
    profile.portrait_photo_enabled = True
    if not was_enabled:
        session.add(PortraitEvent(user_id=user.id, event_type=PortraitEventType.PHOTO_ENABLED))
    await session.commit()
    if old_key and old_key != key:
        try:
            await make_storage().delete(old_key)
        except (HTTPError, OSError, RuntimeError):
            logger.warning("could not remove replaced portrait photo", extra={"user_id": str(user.id)})
    return PortraitPhotoOut(enabled=True, has_photo=True)


@router.patch("/me/portrait-photo", response_model=PortraitPhotoOut)
async def update_portrait_photo_settings(
    payload: PortraitPhotoSettingsIn,
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> PortraitPhotoOut:
    profile = await _profile_for_user(session, user)
    if payload.enabled and not profile.portrait_photo_key:
        raise AppError("portrait_photo_missing", "Upload a portrait photo before enabling photo mode")
    was_enabled = bool(profile.portrait_photo_enabled)
    profile.portrait_photo_enabled = payload.enabled
    if was_enabled != payload.enabled:
        session.add(PortraitEvent(
            user_id=user.id,
            event_type=(PortraitEventType.PHOTO_ENABLED if payload.enabled else PortraitEventType.PHOTO_DISABLED),
        ))
    await session.commit()
    return PortraitPhotoOut(enabled=payload.enabled, has_photo=profile.portrait_photo_key is not None)


@router.delete("/me/portrait-photo", response_model=PortraitPhotoOut)
async def delete_portrait_photo(
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> PortraitPhotoOut:
    profile = await _profile_for_user(session, user)
    was_enabled = bool(profile.portrait_photo_enabled)
    if profile.portrait_photo_key:
        try:
            await make_storage().delete(profile.portrait_photo_key)
        except (HTTPError, OSError, RuntimeError) as exc:
            raise AppError("portrait_photo_unavailable", "Portrait photo storage is unavailable", 503) from exc
    profile.portrait_photo_key = None
    profile.portrait_photo_content_type = None
    profile.portrait_photo_enabled = False
    if was_enabled:
        session.add(PortraitEvent(user_id=user.id, event_type=PortraitEventType.PHOTO_DISABLED))
    await session.commit()
    return PortraitPhotoOut(enabled=False, has_photo=False)


@router.get("/me/portrait-photo", include_in_schema=False)
async def portrait_photo(
    user: CurrentUser = CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> Response:
    profile = await _profile_for_user(session, user)
    if not profile.portrait_photo_key:
        raise NotFound("portrait photo", user.id)
    try:
        data = await make_storage().get(profile.portrait_photo_key)
    except (FileNotFoundError, HTTPError, OSError, RuntimeError):
        raise NotFound("portrait photo", user.id) from None
    content_type = profile.portrait_photo_content_type or "application/octet-stream"
    return Response(content=data, media_type=content_type, headers={"Cache-Control": "private, no-store"})

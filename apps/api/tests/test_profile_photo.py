from types import SimpleNamespace
from uuid import uuid4

import pytest


class Upload:
    def __init__(self, filename: str, data: bytes, content_type: str | None = None):
        self.filename = filename
        self.content_type = content_type
        self.data = data

    async def read(self, _limit: int) -> bytes:
        return self.data


@pytest.mark.asyncio
async def test_uploads_and_enables_a_private_portrait_photo(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models import Profile
    from app.modules.users.routes import upload_portrait_photo

    user = CurrentUser(id=uuid4(), email="learner@example.com")
    profile = Profile(id=user.id)
    stored = {}

    class Session:
        def __init__(self):
            self.added = []

        def add(self, _value):
            self.added.append(_value)

        async def scalar(self, _statement):
            return profile

        async def commit(self):
            return None

    class Storage:
        async def put(self, key, data, content_type):
            stored.update(key=key, data=data, content_type=content_type)
            return key

        async def delete(self, _key):
            return None

    monkeypatch.setattr("app.modules.users.routes.make_storage", lambda: Storage())
    session = Session()
    result = await upload_portrait_photo(
        Upload("portrait.png", b"\x89PNG\r\n\x1a\n"),
        user,
        session,
    )

    assert result.enabled is True
    assert result.has_photo is True
    assert profile.portrait_photo_enabled is True
    assert profile.portrait_photo_key == f"portrait-photos/{user.id}.png"
    assert stored["content_type"] == "image/png"
    assert session.added[0].event_type.value == "portrait_photo_enabled"


@pytest.mark.asyncio
async def test_photo_setting_can_be_disabled_without_deleting_photo():
    from app.core.auth import CurrentUser
    from app.db.models import Profile
    from app.modules.users.routes import PortraitPhotoSettingsIn, update_portrait_photo_settings

    user = CurrentUser(id=uuid4())
    profile = Profile(
        id=user.id,
        portrait_photo_key=f"portrait-photos/{user.id}.jpg",
        portrait_photo_content_type="image/jpeg",
        portrait_photo_enabled=True,
    )

    class Session:
        def __init__(self):
            self.added = []

        def add(self, _value):
            self.added.append(_value)

        async def scalar(self, _statement):
            return profile

        async def commit(self):
            return None

    session = Session()
    result = await update_portrait_photo_settings(
        PortraitPhotoSettingsIn(enabled=False), user, session
    )

    assert result.enabled is False
    assert result.has_photo is True
    assert profile.portrait_photo_key is not None
    assert session.added[0].event_type.value == "portrait_photo_disabled"


@pytest.mark.asyncio
async def test_photo_stream_is_owner_scoped_and_private(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models import Profile
    from app.modules.users.routes import portrait_photo

    user = CurrentUser(id=uuid4())
    profile = Profile(
        id=user.id,
        portrait_photo_key=f"portrait-photos/{user.id}.webp",
        portrait_photo_content_type="image/webp",
        portrait_photo_enabled=True,
    )

    class Session:
        async def scalar(self, _statement):
            return profile

    class Storage:
        async def get(self, _key):
            return b"RIFF0000WEBP"

    monkeypatch.setattr("app.modules.users.routes.make_storage", lambda: Storage())
    response = await portrait_photo(user, Session())

    assert response.body == b"RIFF0000WEBP"
    assert response.media_type == "image/webp"
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.asyncio
async def test_photo_upload_rejects_non_image_content(monkeypatch):
    from app.core.auth import CurrentUser
    from app.db.models import Profile
    from app.modules.users.routes import upload_portrait_photo

    class Session:
        async def scalar(self, _statement):
            return Profile(id=uuid4())

    monkeypatch.setattr("app.modules.users.routes.make_storage", lambda: SimpleNamespace())
    with pytest.raises(Exception) as error:
        await upload_portrait_photo(
            Upload("portrait.txt", b"not an image"),
            CurrentUser(id=uuid4()),
            Session(),
        )

    assert "image" in str(error.value).lower()

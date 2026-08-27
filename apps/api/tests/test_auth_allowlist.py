import uuid

import pytest

from app.core import auth
from app.core.config import Settings
from app.core.errors import Forbidden


def test_production_allowlist_normalizes_addresses():
    settings = Settings(
        environment="production",
        allowed_emails=" AJ05767625@gmail.com, aj472032@gmail.com, aniruddh302004@gmail.com ",
    )

    assert settings.allowed_email_set == {
        "aj05767625@gmail.com",
        "aj472032@gmail.com",
        "aniruddh302004@gmail.com",
    }


@pytest.mark.asyncio
async def test_production_auth_rejects_unlisted_email(monkeypatch):
    monkeypatch.setattr(
        auth,
        "verify_supabase_jwt",
        lambda _token: {"sub": str(uuid.uuid4()), "email": "stranger@example.com"},
    )
    monkeypatch.setattr(
        auth,
        "get_settings",
        lambda: Settings(
            environment="production",
            allowed_emails="aj05767625@gmail.com,aj472032@gmail.com,aniruddh302004@gmail.com",
        ),
    )

    class Request:
        headers = {"authorization": "Bearer test-token"}

    with pytest.raises(Forbidden):
        await auth.get_current_user(Request())

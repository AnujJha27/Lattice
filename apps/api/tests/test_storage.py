from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_supabase_storage_uses_storage_rest_contract(monkeypatch):
    from app.providers.storage import SupabaseStorageProvider

    requests = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, **kwargs):
            requests.append(("POST", url, kwargs))
            return SimpleNamespace(raise_for_status=lambda: None)

        async def request(self, method, url, **kwargs):
            requests.append((method, url, kwargs))
            return SimpleNamespace(raise_for_status=lambda: None)

    monkeypatch.setattr("app.providers.storage.httpx.AsyncClient", lambda **_kwargs: Client())
    provider = SupabaseStorageProvider("https://project.supabase.co", "service-role", "private")

    await provider.put("portrait-photos/user.jpg", b"bytes", "image/jpeg")
    await provider.delete("portrait-photos/user.jpg")

    assert requests[0][0] == "POST"
    assert requests[0][1].endswith("/object/private/portrait-photos/user.jpg")
    assert requests[0][2]["headers"]["x-upsert"] == "true"
    assert requests[1][0] == "DELETE"
    assert requests[1][1].endswith("/object/private")
    assert requests[1][2]["json"] == {"prefixes": ["portrait-photos/user.jpg"]}

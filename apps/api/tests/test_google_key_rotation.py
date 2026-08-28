import pytest


def test_google_key_pool_keeps_primary_first_and_deduplicates():
    from app.core.config import Settings

    settings = Settings(_env_file=None, google_api_key="first", google_api_keys="second, first, third")

    assert settings.google_api_key_pool == ["first", "second", "third"]


class _Usage:
    prompt_token_count = 1
    candidates_token_count = 1


class _Response:
    text = "ok"
    usage_metadata = _Usage()


class _Models:
    def __init__(self, calls, failures):
        self.calls = calls
        self.failures = failures

    async def generate_content(self, **_kwargs):
        key = self.calls[-1]
        if key in self.failures:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return _Response()

    async def embed_content(self, **_kwargs):
        key = self.calls[-1]
        if key in self.failures:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return type("EmbeddingResponse", (), {
            "embeddings": [type("Embedding", (), {"values": [0.1] * 768})()],
        })()


class _Client:
    def __init__(self, key, calls, failures):
        calls.append(key)
        self.aio = type("Aio", (), {
            "models": _Models(calls, failures),
        })()


@pytest.mark.asyncio
async def test_gemini_text_rotates_to_next_key_on_quota_error(monkeypatch):
    from app.providers.gemini import GeminiProvider

    calls = []
    monkeypatch.setattr(
        "app.providers.gemini.genai.Client",
        lambda *, api_key: _Client(api_key, calls, {"first"}),
    )

    response = await GeminiProvider(api_keys=["first", "second"]).generate_text("hello")

    assert response.text == "ok"
    assert calls == ["first", "second"]


@pytest.mark.asyncio
async def test_gemini_embeddings_rotate_to_next_key_on_quota_error(monkeypatch):
    from app.providers.embedding import GeminiEmbeddingProvider

    calls = []
    monkeypatch.setattr(
        "app.providers.embedding.genai.Client",
        lambda *, api_key: _Client(api_key, calls, {"first"}),
    )

    vectors = await GeminiEmbeddingProvider(api_keys=["first", "second"]).embed(["hello"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 768
    assert calls == ["first", "second"]

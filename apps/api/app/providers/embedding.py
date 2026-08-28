"""Embedding provider abstraction. Default implementation: Gemini embedding-001."""
from typing import Protocol

from google import genai

from app.db.models.concept import EMBEDDING_DIM
from app.providers.google import GoogleKeyRotation


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbeddingProvider:
    provider_name = "gemini"
    model_name = "gemini-embedding-001"

    def __init__(self, model: str | None = None, api_keys: list[str] | None = None):
        from app.core.config import get_settings
        settings = get_settings()
        self.model_name = model or settings.gemini_embedding_model
        self._keys = api_keys or settings.google_api_key_pool
        self._rotation = GoogleKeyRotation(self._keys, genai.Client)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        result = await self._rotation.call(lambda client: client.aio.models.embed_content(
            model=self.model_name,
            contents=texts,
            config={"output_dimensionality": EMBEDDING_DIM},
        ))
        vectors = [list(e.values) for e in result.embeddings]
        if len(vectors) != len(texts):
            raise ValueError(f"expected {len(texts)} embeddings, got {len(vectors)}")
        return vectors

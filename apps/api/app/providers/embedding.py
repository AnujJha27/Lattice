"""Embedding provider abstraction. Default implementation: Gemini text-embedding-004."""
from typing import Protocol

from google import genai

from app.db.models.concept import EMBEDDING_DIM


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class GeminiEmbeddingProvider:
    provider_name = "gemini"
    model_name = "gemini-embedding-001"

    def __init__(self, model: str | None = None):
        from app.core.config import get_settings
        self._client = genai.Client(api_key=get_settings().google_api_key)
        self.model_name = model or get_settings().gemini_embedding_model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        result = await self._client.aio.models.embed_content(
            model=self.model_name,
            contents=texts,
            config={"output_dimensionality": EMBEDDING_DIM},
        )
        vectors = [list(e.values) for e in result.embeddings]
        if len(vectors) != len(texts):
            raise ValueError(f"expected {len(texts)} embeddings, got {len(vectors)}")
        return vectors

"""Gemini implementation of LLMProvider via google-genai.

Structured generation uses response_mime_type=application/json +
response_schema so the model is constrained to our Pydantic-derived schemas.
"""
import json
import time
from typing import Any

from google import genai
from google.genai import types as gtypes

from app.providers.llm import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, model: str | None = None):
        from app.core.config import get_settings
        self._client = genai.Client(api_key=get_settings().google_api_key)
        self.model = model or get_settings().gemini_model

    async def generate_text(self, prompt: str, *, system: str | None = None,
                            temperature: float = 0.7) -> LLMResponse:
        started = time.perf_counter()
        config = gtypes.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model, contents=prompt, config=config
        )
        latency = int((time.perf_counter() - started) * 1000)
        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=response.text or "",
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            model=self.model,
            provider=self.provider_name,
            latency_ms=latency,
        )

    async def generate_structured(self, prompt: str, schema: dict[str, Any], *,
                                  system: str | None = None) -> LLMResponse:
        started = time.perf_counter()
        config = gtypes.GenerateContentConfig(
            temperature=0.4,
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        )
        response = await self._client.aio.models.generate_content(
            model=self.model, contents=prompt, config=config
        )
        latency = int((time.perf_counter() - started) * 1000)
        raw = response.text or "{}"
        try:
            parsed: Any = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=raw,
            structured=parsed,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            model=self.model,
            provider=self.provider_name,
            latency_ms=latency,
        )

    async def stream_text(self, prompt: str, *, system: str | None = None):
        config = gtypes.GenerateContentConfig(temperature=0.7, system_instruction=system)
        async for chunk in self._client.aio.models.generate_content_stream(
            model=self.model, contents=prompt, config=config
        ):
            if chunk.text:
                yield chunk.text

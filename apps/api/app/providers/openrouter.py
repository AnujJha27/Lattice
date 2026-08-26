"""OpenRouter provider — OpenAI-compatible API, free models available.

Structured generation uses JSON mode + lenient parsing (free models vary in
schema adherence), then Pydantic validation happens in the caller. If a model
proves unreliable for a schema, switch models via OPENROUTER_MODEL — the
abstraction stays the same.
"""
import json
import re
import time
from typing import Any

import httpx

from app.providers.llm import LLMResponse

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


# Verified free-tier pool, GLM-5.2-adjacent quality. Tested 2026-08:
# all three return valid structured JSON. 100B+ MoE class only — no small models.
DEFAULT_FALLBACKS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m3:free",
]


class OpenRouterProvider:
    provider_name = "openrouter"

    def __init__(self, api_key: str, model: str,
                 fallbacks: list[str] | None = None):
        self._api_key = api_key
        self.model = model
        # Sticky rotation: start at the primary; after a 429 we advance and
        # stay on the new model until IT rate-limits. Avoids hammering one
        # rate-limited model on every request.
        self._pool: list[str] = [model]
        for candidate in (fallbacks if fallbacks is not None else DEFAULT_FALLBACKS):
            if candidate not in self._pool:
                self._pool.append(candidate)
        self._current = 0

    @property
    def model(self) -> str:
        return self._pool[self._current]

    @model.setter
    def model(self, value: str) -> None:
        self._pool = [value]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lattice.local",
            "X-Title": "Lattice",
        }

    async def _chat(self, messages: list[dict], temperature: float,
                    json_mode: bool) -> dict:
        body: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for offset in range(len(self._pool)):
            index = (self._current + offset) % len(self._pool)
            body["model"] = self._pool[index]
            async with httpx.AsyncClient(timeout=120) as client:
                try:
                    response = await client.post(ENDPOINT, headers=self._headers(), json=body)
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    # 429/5xx → try the next model in the pool; anything else
                    # (400, 401, 404) is a real problem, fail immediately.
                    if exc.response.status_code in (429, 500, 502, 503) and offset < len(self._pool) - 1:
                        last_error = exc
                        continue
                    raise
                data = response.json()
                # Some models return HTTP 200 with an error payload and no
                # choices (content filters, upstream hiccups) — cycle onward.
                if not data.get("choices"):
                    last_error = RuntimeError(
                        f"{self._pool[index]} returned no choices: "
                        f"{str(data.get('error', data))[:150]}"
                    )
                    continue
                self._current = index  # sticky: stay on this model
                return data
        assert last_error is not None
        raise last_error

    async def generate_text(self, prompt: str, *, system: str | None = None,
                            temperature: float = 0.7) -> LLMResponse:
        started = time.perf_counter()
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt},
        ]
        data = await self._chat(messages, temperature, json_mode=False)
        latency = int((time.perf_counter() - started) * 1000)
        usage = data.get("usage", {})
        return LLMResponse(
            text=data["choices"][0]["message"]["content"] or "",
            model=self.model,
            provider=self.provider_name,
            input_tokens=usage.get("prompt_tokens", 0) or 0,
            output_tokens=usage.get("completion_tokens", 0) or 0,
            latency_ms=latency,
        )

    async def generate_structured(self, prompt: str, schema: dict[str, Any] | type, *,
                                  system: str | None = None) -> LLMResponse:
        started = time.perf_counter()
        # Accept a Pydantic model class (as Gemini does) or a plain dict.
        if not isinstance(schema, dict) and hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()
        schema_hint = json.dumps(schema, ensure_ascii=False)[:4000]
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": (
                f"{prompt}\n\nReturn ONLY a JSON object matching this shape "
                f"(field names and types must match exactly):\n{schema_hint}"
            )},
        ]
        try:
            data = await self._chat(messages, temperature=0.4, json_mode=True)
            raw = data["choices"][0]["message"]["content"] or ""
        except httpx.HTTPStatusError:
            # Some free models reject response_format; retry without it.
            data = await self._chat(messages, temperature=0.4, json_mode=False)
            raw = data["choices"][0]["message"]["content"] or ""

        latency = int((time.perf_counter() - started) * 1000)
        usage = data.get("usage", {})
        return LLMResponse(
            text=raw,
            structured=_extract_json(raw),
            input_tokens=usage.get("prompt_tokens", 0) or 0,
            output_tokens=usage.get("completion_tokens", 0) or 0,
            latency_ms=latency,
            model=self.model,
            provider=self.provider_name,
        )

    async def stream_text(self, prompt: str, *, system: str | None = None):
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt},
        ]
        body = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST", ENDPOINT, headers=self._headers(), json=body
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        return
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {}).get("content")
                    if delta:
                        yield delta


def _extract_json(raw: str) -> Any | None:
    """Lenient JSON extraction: bare object, fenced block, or first balanced object."""
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start = raw.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(raw[start : i + 1])
                    except json.JSONDecodeError:
                        return None
    return None

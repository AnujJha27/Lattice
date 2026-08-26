"""LLM provider abstraction. Features never import a model SDK directly."""
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int | None = None
    structured: Any | None = None  # populated by generate_structured


class LLMProvider(Protocol):
    provider_name: str

    async def generate_text(self, prompt: str, *, system: str | None = None,
                            temperature: float = 0.7) -> LLMResponse: ...

    async def generate_structured(self, prompt: str, schema: dict[str, Any] | type, *,
                                  system: str | None = None) -> LLMResponse: ...

    def stream_text(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]: ...

"""Web search abstraction for source discovery.

Implementations must return normalized candidates; ranking and dedup happen
in the sources domain, not here.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    published: date | None = None
    provider: str = ""
    extra: dict = field(default_factory=dict)


class WebSearchProvider(Protocol):
    provider_name: str

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]: ...

"""Source candidate contracts shared by discovery, ranking, and routes."""
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class SourceCandidate(BaseModel):
    """A discovered (not yet persisted) source."""

    title: str
    url: str
    snippet: str = ""
    published: date | None = None
    provider: str = ""  # tavily | arxiv | openalex
    source_type: str = "OTHER"
    authority: float = 0.4
    publisher: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    authors: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class DiscoverRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    domain: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=10, ge=1, le=25)


class RankedCandidate(BaseModel):
    candidate: SourceCandidate
    factors: dict[str, Any]  # floats + the policy name (spec §19: debuggable rankings)


class DiscoverResponse(BaseModel):
    candidates: list[RankedCandidate]
    policy: str
    deduped_from: int  # how many raw hits before dedup


class SourceAccept(BaseModel):
    """Persist a discovered candidate into the library and start ingestion."""

    title: str
    url: str
    source_type: str = "OTHER"
    authority: float = Field(default=0.4, ge=0, le=1)
    published: date | None = None
    publisher: str | None = None
    authors: list[str] = []
    doi: str | None = None
    arxiv_id: str | None = None
    concept_id: str | None = None  # optional immediate link to a Brain concept


class SourceNote(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=20, max_length=400_000)
    source_type: str = "USER_SOURCE"


class SourceOut(BaseModel):
    id: str
    title: str
    url: str | None
    source_type: str
    origin: str
    publisher: str | None
    authors: list[str]
    published: date | None
    ingest_status: str
    ingest_error: str | None = None
    chunk_count: int = 0
    created_at: str | None = None

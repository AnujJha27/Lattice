"""Pathway contracts — API and structured generation schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


# ── Structured generation schema (what Gemini must return) ──────────
class GeneratedConcept(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    domain: str = Field(default="", max_length=100)
    section: int = Field(ge=0)
    description: str = Field(default="", max_length=1000)
    difficulty: int = Field(default=2, ge=1, le=5)
    prerequisites: list[str] = Field(default_factory=list, max_length=20)


class GeneratedSection(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=600)


class GeneratedPathway(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1500)
    sections: list[GeneratedSection] = Field(min_length=1, max_length=15)
    concepts: list[GeneratedConcept] = Field(min_length=1, max_length=60)


# ── API contracts ───────────────────────────────────────────────────
class PathwayCreate(BaseModel):
    topic: str = Field(min_length=3, max_length=300)
    target_depth: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")


class PathwayConceptOut(BaseModel):
    concept_id: str
    name: str
    description: str | None
    difficulty: int | None
    mastery_score: float
    state: str
    position: int


class PathwaySectionOut(BaseModel):
    id: str
    position: int
    title: str
    summary: str | None
    concepts: list[PathwayConceptOut]


class PathwayOut(BaseModel):
    id: str
    title: str
    topic: str | None
    status: str
    created_at: datetime | None
    section_count: int = 0
    concept_count: int = 0
    target_depth: str = "beginner"
    next_depth: str | None = None


class PathwayDetail(PathwayOut):
    description: str | None = None
    sections: list[PathwaySectionOut] = []
    skipped_edges: int = 0

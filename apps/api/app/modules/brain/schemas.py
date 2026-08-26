"""Pydantic contracts for the Brain API."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BrainNode(BaseModel):
    id: UUID
    name: str = Field(serialization_alias="name")
    domain: str | None = None
    difficulty: int | None = None
    mastery_score: float = 0
    state: str = "UNSEEN"
    interest_score: float = 0


class BrainEdge(BaseModel):
    source: UUID
    target: UUID
    type: str
    confidence: float | None = None
    created_by: str | None = None


class BrainGraphResponse(BaseModel):
    nodes: list[BrainNode]
    edges: list[BrainEdge]
    generated_at: datetime


class ConceptCreate(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    domain: str | None = Field(default=None, max_length=100)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    add_interest: bool = True  # link to the user's Brain on creation


class ConceptOut(BaseModel):
    id: UUID
    canonical_name: str
    description: str | None
    domain: str | None
    difficulty: int | None


class ConceptDetail(ConceptOut):
    prerequisites: list[ConceptOut] = []
    dependents: list[ConceptOut] = []
    related: list[ConceptOut] = []
    mastery_score: float = 0
    state: str = "UNSEEN"
    in_brain: bool = False


class EdgeCreate(BaseModel):
    target_id: UUID
    type: str = "PREREQUISITE"


class CombineRequest(BaseModel):
    concept_a: UUID
    concept_b: UUID


class BridgeIdea(BaseModel):
    """What the LLM must return when fusing two concepts."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    domain: str | None = None
    difficulty: int = Field(default=3, ge=1, le=5)

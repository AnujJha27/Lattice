"""API contracts for immutable Intellectual Portrait snapshots."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.portrait import PortraitEventType
from app.modules.visual_sources.schemas import PortraitVisualSource


class PortraitSummary(BaseModel):
    concept_count: int
    mastered_concept_count: int
    domain_count: int
    active_frontier_count: int
    dominant_domains: list[str] = Field(default_factory=list)
    strongest_thread: str | None = None
    emerging_thread: str | None = None
    primary_bridge: str | None = None
    primary_frontier: str | None = None


class PortraitDomain(BaseModel):
    id: str
    name: str
    concept_count: int
    mastery: float
    activity: float
    interest: float
    recency: float
    breadth: float
    depth: float
    portrait_weight: float
    dominant_concept_ids: list[str] = Field(default_factory=list)


class PortraitNode(BaseModel):
    id: str
    name: str
    domain: str
    score: float
    mastery: float
    activity: float
    reason: str
    connected_domains: list[str] = Field(default_factory=list)


class PortraitThread(BaseModel):
    id: str
    name: str
    score: float
    concept_ids: list[str] = Field(default_factory=list)
    reason: str


class PortraitConnection(BaseModel):
    source_id: str
    target_id: str
    type: str
    confidence: float | None = None


class PortraitChange(BaseModel):
    kind: str
    text: str


class PortraitModel(BaseModel):
    snapshot_id: str
    generated_at: datetime
    version: int
    algorithm_version: str
    config_version: str
    input_hash: str
    summary: PortraitSummary
    domains: list[PortraitDomain] = Field(default_factory=list)
    anchors: list[PortraitNode] = Field(default_factory=list)
    bridges: list[PortraitNode] = Field(default_factory=list)
    frontiers: list[PortraitNode] = Field(default_factory=list)
    emerging_threads: list[PortraitThread] = Field(default_factory=list)
    dormant_threads: list[PortraitThread] = Field(default_factory=list)
    connections: list[PortraitConnection] = Field(default_factory=list)
    visual_sources: list[PortraitVisualSource] = Field(default_factory=list)
    evolution: dict[str, float] = Field(default_factory=dict)
    narrative: str
    confidence: dict[str, float] = Field(default_factory=dict)
    changes_since_previous: list[PortraitChange] = Field(default_factory=list)


class PortraitElementExplanation(BaseModel):
    snapshot_id: str
    kind: str
    element: PortraitNode | PortraitThread


class PortraitDebugFactor(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float


class PortraitDebugElement(BaseModel):
    kind: str
    id: str
    name: str
    score: float
    threshold: str
    selected: bool
    suppressed_by_evidence: bool = False
    factors: list[PortraitDebugFactor] = Field(default_factory=list)


class PortraitDebugReport(BaseModel):
    snapshot_id: str | None = None
    input_hash: str
    algorithm_version: str
    config_version: str
    elements: list[PortraitDebugElement] = Field(default_factory=list)
    visual_sources: list[PortraitDebugElement] = Field(default_factory=list)


class PortraitVisualRefresh(BaseModel):
    job_id: str
    snapshot_id: str
    status: str
    portrait: PortraitModel | None = None
    error: str | None = None


class PortraitRefresh(BaseModel):
    job_id: str
    status: str
    portrait: PortraitModel | None = None
    error: str | None = None


class PortraitEventIn(BaseModel):
    event_type: PortraitEventType
    snapshot_id: UUID | None = None
    element_id: str | None = Field(default=None, min_length=1, max_length=128)

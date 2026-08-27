from pydantic import BaseModel, Field


class VisualAssetOut(BaseModel):
    id: str
    title: str
    source_url: str
    canonical_url: str
    creator: str | None = None
    institution: str | None = None
    date: str | None = None
    license: str | None = None
    rights_class: str
    attribution_text: str | None = None
    image_url: str
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None
    provider: str
    relevance_score: float
    aesthetic_score: float
    rights_score: float
    quality_score: float
    cached_image_url: str | None = None


class PortraitVisualSource(BaseModel):
    asset_id: str
    represents: str
    concept_ids: list[str] = Field(default_factory=list)
    portrait_role: str
    asset: VisualAssetOut

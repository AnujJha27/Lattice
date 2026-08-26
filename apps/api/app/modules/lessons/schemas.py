"""Lesson contracts. Content is schema-validated; citations reference only
source indexes the backend provided to the model (§18: never fabricate).

v2 "book chapter" structure: multi-section chapters with per-section
equations and key takeaways. Legacy flat-paragraph lessons still validate.
"""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class LessonParagraph(BaseModel):
    text: str = Field(min_length=1)
    source_ids: list[int] = Field(default_factory=list)  # indexes into provided contexts


class LessonSection(BaseModel):
    heading: str = Field(min_length=1, max_length=200)
    paragraphs: list[LessonParagraph] = Field(min_length=1, max_length=10)
    equations: list[str] = Field(default_factory=list, max_length=8)
    key_points: list[str] = Field(default_factory=list, max_length=8)


class LessonContent(BaseModel):
    intuition: str = Field(min_length=1)  # plain-language core idea (may be uncited)
    sections: list[LessonSection] = Field(default_factory=list, max_length=12)
    paragraphs: list[LessonParagraph] = Field(default_factory=list, max_length=12)  # legacy
    examples: list[str] = Field(default_factory=list, max_length=10)
    common_mistakes: list[str] = Field(default_factory=list, max_length=10)
    equations: list[str] = Field(default_factory=list, max_length=14)  # legacy

    @model_validator(mode="after")
    def has_content(self):
        if not self.sections and not self.paragraphs:
            raise ValueError("lesson needs either sections or paragraphs")
        return self

    def all_paragraphs(self) -> list[LessonParagraph]:
        return [p for s in self.sections for p in s.paragraphs] + self.paragraphs


class SourceContext(BaseModel):
    """A grounding excerpt handed to the model with a stable integer index."""

    index: int
    source_id: str
    title: str
    publisher: str | None = None
    year: int | None = None
    authors: list[str] = []
    url: str | None = None
    excerpt: str
    from_snippet: bool = False  # discovery fallback — page not yet ingested


class LessonOut(BaseModel):
    concept_id: str
    title: str
    content: LessonContent
    grounding: str  # GROUNDED | MIXED | GENERATED
    sources: list[SourceContext]
    generated_at: datetime | None
    cached: bool = False


class GenerateLessonResponse(BaseModel):
    lesson: LessonOut
    context_count: int
    input_tokens: int = 0
    output_tokens: int = 0

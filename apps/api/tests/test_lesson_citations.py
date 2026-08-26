"""Tests for the hard-citation-validation rules (§18)."""
from __future__ import annotations

from app.modules.lessons.generator import grounding_status, validate_citations
from app.modules.lessons.schemas import LessonContent, LessonParagraph


def _content(*paragraph_specs: tuple[list[int], ...]) -> LessonContent:
    specs = list(paragraph_specs)
    # Schema requires >= 2 paragraphs; pad with a neutral one for single-case tests.
    if len(specs) == 1:
        specs.append(())
    return LessonContent(
        intuition="Core idea.",
        paragraphs=[
            LessonParagraph(text=f"Paragraph {i}.", source_ids=list(ids))
            for i, ids in enumerate(specs)
        ],
    )


class TestValidateCitations:
    def test_valid_ids_kept(self):
        content = _content([0, 1], [1])
        cleaned, dropped = validate_citations(content, valid_indexes={0, 1})
        assert dropped == 0
        assert cleaned.paragraphs[0].source_ids == [0, 1]

    def test_fabricated_ids_stripped(self):
        content = _content([0, 7])  # index 7 never provided to the model
        cleaned, dropped = validate_citations(content, valid_indexes={0})
        assert dropped == 1
        assert cleaned.paragraphs[0].source_ids == [0]

    def test_all_invalid_becomes_uncited_paragraph(self):
        content = _content([5, 6])
        cleaned, dropped = validate_citations(content, valid_indexes={0, 1})
        assert dropped == 2
        assert cleaned.paragraphs[0].source_ids == []
        # paragraph survives — only the false attribution is removed

    def test_duplicates_deduped(self):
        content = _content([2, 2, 2])
        cleaned, _ = validate_citations(content, valid_indexes={2})
        assert cleaned.paragraphs[0].source_ids == [2]


class TestGroundingStatus:
    def test_grounded_when_every_paragraph_cited(self):
        assert grounding_status(_content([0], [1])) == "GROUNDED"

    def test_mixed_when_partially_cited(self):
        assert grounding_status(_content([0], [])) == "MIXED"

    def test_generated_when_no_citations(self):
        assert grounding_status(_content([], [], [])) == "GENERATED"

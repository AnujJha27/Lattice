"""Unit tests for pathway generation validation (no LLM, no DB)."""
from __future__ import annotations

from app.modules.pathways.generator import validate_generated
from app.modules.pathways.schemas import (
    GeneratedConcept,
    GeneratedPathway,
    GeneratedSection,
)


def _pathway(concepts: list[GeneratedConcept]) -> GeneratedPathway:
    return GeneratedPathway(
        title="Test pathway",
        sections=[GeneratedSection(title=f"Section {i}") for i in range(3)],
        concepts=[
            concept.model_copy(update={"domain": concept.domain or "Test Domain"})
            for concept in concepts
        ],
    )


class TestValidateGenerated:
    def test_domain_is_normalized_and_backward_prerequisite_is_dropped(self):
        result, skipped = validate_generated(_pathway([
            GeneratedConcept(name="Foundations", section=0, domain=" Formal Verification "),
            GeneratedConcept(
                name="Advanced", section=1, domain="Formal   Verification",
                prerequisites=["Foundations"],
            ),
            GeneratedConcept(
                name="Backward", section=0, domain="Formal Verification",
                prerequisites=["Advanced"],
            ),
        ]))
        assert [concept.domain for concept in result.concepts] == [
            "Formal Verification", "Formal Verification", "Formal Verification",
        ]
        assert result.concepts[2].prerequisites == []
        assert skipped == 1

    def test_clean_pathway_unchanged(self):
        result, skipped = validate_generated(_pathway([
            GeneratedConcept(name="Vectors", section=0, prerequisites=[]),
            GeneratedConcept(name="Matrices", section=1, prerequisites=["Vectors"]),
        ]))
        assert skipped == 0
        assert len(result.concepts) == 2
        assert result.concepts[1].prerequisites == ["Vectors"]

    def test_unknown_prerequisite_dropped(self):
        result, skipped = validate_generated(_pathway([
            GeneratedConcept(name="A", section=0),
            GeneratedConcept(name="B", section=1, prerequisites=["Nonexistent"]),
        ]))
        assert result.concepts[1].prerequisites == []
        assert skipped >= 1

    def test_cycle_edges_skipped_not_fatal(self):
        result, skipped = validate_generated(_pathway([
            GeneratedConcept(name="A", section=0, prerequisites=["B"]),
            GeneratedConcept(name="B", section=0, prerequisites=["A"]),
        ]))
        assert skipped >= 1  # at least one edge dropped to break the cycle
        # both concepts survive — only the offending edge is removed
        assert len(result.concepts) == 2

    def test_section_index_clamped(self):
        result, _ = validate_generated(_pathway([
            GeneratedConcept(name="A", section=99),
        ]))
        assert result.concepts[0].section == 2  # len(sections)-1

    def test_duplicate_names_removed(self):
        result, _ = validate_generated(_pathway([
            GeneratedConcept(name="Eigenvalues", section=0),
            GeneratedConcept(name="eigenvalues", section=1),
        ]))
        assert len(result.concepts) == 1

    def test_self_prerequisite_removed(self):
        result, _ = validate_generated(_pathway([
            GeneratedConcept(name="A", section=0, prerequisites=["A"]),
        ]))
        assert result.concepts[0].prerequisites == []

    def test_transitive_chain_preserved(self):
        result, skipped = validate_generated(_pathway([
            GeneratedConcept(name="Foundations", section=0),
            GeneratedConcept(name="Middle", section=1, prerequisites=["Foundations"]),
            GeneratedConcept(name="Advanced", section=2, prerequisites=["Middle", "Foundations"]),
        ]))
        assert skipped == 0
        advanced = next(c for c in result.concepts if c.name == "Advanced")
        assert set(advanced.prerequisites) == {"Middle", "Foundations"}

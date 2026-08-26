# Brain Graph Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every concept a domain and replace faulty AI-owned graph edges through a reviewable regeneration process.

**Architecture:** Pathway generation supplies and validates a broad domain plus section-ordered prerequisites. A Windows-venv audit script produces a proposed JSON graph before `--apply` deletes and replaces only AI-owned rows. The API carries edge provenance so the web graph does not use related links for island membership.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic, PostgreSQL/pgvector, existing LLM provider, pytest.

**Spec:** `docs/superpowers/specs/2026-08-27-brain-graph-repair-design.md`

## Global Constraints

- Use the existing API Windows virtual environment for database and regeneration commands.
- Preserve all `created_by = 'user'` edge rows.
- Do not mutate data without `--apply`; write a report first.
- Add no dependencies.

---

### Task 1: Domain-aware pathway validation

**Files:**
- Modify: `apps/api/app/modules/pathways/schemas.py`, `apps/api/app/modules/pathways/generator.py`
- Test: `apps/api/tests/test_pathway_validation.py`

**Interfaces:**
- Produces `GeneratedConcept.domain: str` and `validate_generated(raw) -> tuple[GeneratedPathway, int]` with normalized domains and forward-only prerequisite references.

- [ ] **Step 1: Write failing tests**

```python
def test_rejects_a_blank_domain_and_backward_prerequisite():
    result, skipped = validate_generated(_pathway([
        GeneratedConcept(name="A", domain="", section=0),
        GeneratedConcept(name="B", domain="Formal Verification", section=1, prerequisites=["A"]),
    ]))
    assert [c.name for c in result.concepts] == ["B"]
    assert skipped == 1
```

- [ ] **Step 2: Run the test with the API Windows venv; confirm it fails.**
- [ ] **Step 3: Add `domain`, normalize it, and retain only prerequisites from an earlier section.**
- [ ] **Step 4: Re-run the focused test and `pytest tests/test_pathway_validation.py`.**

### Task 2: Persist domains and expose edge provenance

**Files:**
- Modify: `apps/api/app/modules/pathways/generator.py`, `apps/api/app/modules/brain/schemas.py`, `apps/api/app/modules/brain/service.py`
- Test: `apps/api/tests/test_brain_api.py`

**Interfaces:**
- Produces `BrainEdge(source, target, type, confidence, created_by)` and persists `ConceptCreate(domain=concept_spec.domain)`.

- [ ] **Step 1: Write a failing API schema test asserting confidence and created_by survive graph serialization.**
- [ ] **Step 2: Run it; confirm the fields are absent.**
- [ ] **Step 3: Add the fields and pass domains into concept creation.**
- [ ] **Step 4: Re-run the focused API test.**

### Task 3: Dry-run graph audit and explicit apply

**Files:**
- Create: `apps/api/scripts/regenerate_brain_graph.py`
- Test: `apps/api/tests/test_brain_regeneration.py`

**Interfaces:**
- `python scripts/regenerate_brain_graph.py --report path.json` writes proposed domain and AI-edge changes.
- `python scripts/regenerate_brain_graph.py --report path.json --apply` performs exactly the reviewed changes; it excludes user edges.

- [ ] **Step 1: Write a failing unit test where a user edge remains while an AI prerequisite is replaced.**
- [ ] **Step 2: Run it; confirm the script module is absent.**
- [ ] **Step 3: Implement report construction, LLM structured audit, and the `--apply` guard.**
- [ ] **Step 4: Run the focused test and inspect a live dry-run report with the Windows venv.**

### Task 4: Make islands structural only

**Files:**
- Modify: `apps/web/components/brain/BrainCanvas.tsx`, `apps/web/types/brain.ts`
- Test: `apps/web/test/brainGraph.test.ts`

**Interfaces:**
- Island community detection consumes only `PREREQUISITE` and `PART_OF`; `RELATED_TO` stays visible as a cross-island edge.

- [ ] **Step 1: Write a failing graph test with a related-only connection that must not merge two islands.**
- [ ] **Step 2: Run the test; confirm it fails.**
- [ ] **Step 3: Filter Louvain’s input to structural edges while retaining all edges for rendering.**
- [ ] **Step 4: Re-run the browser graph test and web typecheck.**

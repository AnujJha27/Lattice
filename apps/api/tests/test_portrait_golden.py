"""Deterministic portrait fixtures from the roadmap's A–E examples."""
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid5

from app.db.models import Concept, ConceptEdge
from app.db.models.concept import EdgeType
from app.db.models.learning import UserConcept
from app.modules.portrait.service import build_portrait

NOW = datetime(2026, 8, 27, tzinfo=UTC)
USER_ID = UUID("00000000-0000-0000-0000-000000000001")
FIXTURE_NAMESPACE = UUID("00000000-0000-0000-0000-000000000002")


class Result:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class PortraitSession:
    def __init__(self, pairs, edges=(), goals=(), reviews=()):
        self.results = iter((Result(pairs), Result(edges), Result(goals), Result(reviews)))

    async def execute(self, _statement):
        return next(self.results)


def learner(name, domain, *, mastery=0, interactions=0, successful=0, tested_at=None):
    concept = Concept(id=uuid5(FIXTURE_NAMESPACE, f"{domain}:{name}"), canonical_name=name, domain=domain)
    state = UserConcept(
        user_id=USER_ID,
        concept_id=concept.id,
        mastery_score=mastery,
        interest_score=50,
        attempt_count=interactions,
        review_count=interactions,
        successful_reviews=successful,
        last_tested_at=tested_at,
    )
    return concept, state


def related(source, target):
    return ConceptEdge(
        source_id=source.id,
        target_id=target.id,
        type=EdgeType.RELATED_TO,
        confidence=0.9,
    )


async def portrait(pairs, edges=(), goals=(), reviews=()):
    session = PortraitSession(pairs, edges, goals, reviews)
    return await build_portrait(session, SimpleNamespace(id=USER_ID), now=NOW)


async def test_new_user_fixture_stays_sparse():
    pairs = [learner("New Concept", "Uncategorized")]

    result = await portrait(pairs)

    assert result.summary.concept_count == 1
    assert result.summary.dominant_domains == []
    assert result.anchors == []
    assert result.frontiers == []
    assert result.emerging_threads == []
    assert result.confidence["overall"] == 0
    assert result.narrative.startswith("Your portrait is still forming")


async def test_mathematics_specialist_fixture_has_a_math_core():
    pairs = [
        learner("Linear Algebra", "Mathematics", mastery=80, interactions=4, successful=4, tested_at=NOW),
        learner("Graph Theory", "Mathematics", mastery=80, interactions=4, successful=4, tested_at=NOW),
        learner("Real Analysis", "Mathematics", mastery=80, interactions=4, successful=4, tested_at=NOW),
    ]

    result = await portrait(pairs)

    assert result.summary.dominant_domains == ["Mathematics"]
    assert result.summary.mastered_concept_count == 3
    assert {item.name for item in result.anchors} == {item[0].canonical_name for item in pairs}
    assert result.domains[0].depth > 0.5


async def test_cross_domain_fixture_identifies_linear_algebra_as_bridge():
    linear, linear_state = learner(
        "Linear Algebra", "Mathematics", mastery=80, interactions=4, successful=4, tested_at=NOW
    )
    machine_learning, ml_state = learner("Diffusion Models", "Machine Learning", interactions=2, tested_at=NOW)
    physics, physics_state = learner("Quantum Mechanics", "Physics", interactions=2, tested_at=NOW)
    graph, graph_state = learner("Graph Theory", "Graph Theory", interactions=2, tested_at=NOW)

    result = await portrait(
        [(linear, linear_state), (machine_learning, ml_state), (physics, physics_state), (graph, graph_state)],
        [related(linear, machine_learning), related(linear, physics), related(linear, graph)],
    )

    bridge = next(item for item in result.bridges if item.name == "Linear Algebra")
    assert result.summary.primary_bridge == "Linear Algebra"
    assert bridge.connected_domains == ["Graph Theory", "Machine Learning", "Physics"]


async def test_formal_methods_fixture_has_an_emerging_thread():
    pairs = [
        learner("Lean", "Formal Methods", interactions=3, tested_at=NOW),
        learner("Dependent Types", "Formal Methods", interactions=3, tested_at=NOW),
        learner("Proof Assistants", "Formal Methods", interactions=3, tested_at=NOW),
        learner("Verification", "Formal Methods", interactions=3, tested_at=NOW),
    ]

    result = await portrait(
        pairs,
        [related(pairs[index][0], pairs[index + 1][0]) for index in range(len(pairs) - 1)],
    )

    assert [thread.name for thread in result.emerging_threads] == ["Formal Methods"]
    assert result.emerging_threads[0].concept_ids == [str(item[0].id) for item in pairs]


async def test_dormant_domain_fixture_remains_visible_but_quieter():
    old = NOW - timedelta(days=60)
    pairs = [
        learner("Graph Theory", "Graph Theory", mastery=80, interactions=4, successful=4, tested_at=old),
        learner("Centrality", "Graph Theory", mastery=80, interactions=4, successful=4, tested_at=old),
        learner("Spectral Graphs", "Graph Theory", mastery=80, interactions=4, successful=4, tested_at=old),
    ]

    result = await portrait(pairs)

    assert [thread.name for thread in result.dormant_threads] == ["Graph Theory"]
    assert result.dormant_threads[0].concept_ids == [str(item[0].id) for item in pairs]
    assert result.emerging_threads == []

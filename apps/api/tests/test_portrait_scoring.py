import asyncio
from dataclasses import asdict
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.db.models import Concept
from app.db.models.learning import UserConcept
from app.modules.portrait import service as portrait_service
from app.modules.portrait.schemas import PortraitModel, PortraitSummary
from app.modules.portrait.service import (
    PortraitConfig,
    _changes,
    _facts,
    anchor_score,
    build_portrait,
    frontier_score,
    get_portrait,
    has_portrait_evidence,
    is_emerging_thread,
    stable_input_hash,
)


def test_input_hash_is_stable_across_record_order():
    records = [{"id": "b", "mastery": 20}, {"id": "a", "mastery": 80}]
    assert stable_input_hash(records, [("b", "a")]) == stable_input_hash(
        list(reversed(records)), [("b", "a")]
    )


def test_input_hash_changes_when_portrait_context_changes():
    records = [{"id": "a", "name": "Graph Theory", "domain": "Mathematics"}]
    assert stable_input_hash(records, [], context={"active_goal_ids": []}) != stable_input_hash(
        records, [], context={"active_goal_ids": ["a"]}
    )


def test_input_hash_changes_when_scoring_profile_changes():
    records = [{"id": "a", "name": "Graph Theory", "domain": "Mathematics"}]
    default_context = {"scoring_config": asdict(PortraitConfig())}
    tuned_context = {"scoring_config": asdict(PortraitConfig(min_interactions=11))}

    assert stable_input_hash(records, [], context=default_context) != stable_input_hash(
        records, [], context=tuned_context
    )


def test_input_hash_preserves_edge_direction_and_type():
    records = [{"id": "a"}, {"id": "b"}]
    prerequisite = stable_input_hash(records, [("a", "b", "PREREQUISITE", None)])
    related = stable_input_hash(records, [("a", "b", "RELATED_TO", None)])
    reversed_edge = stable_input_hash(records, [("b", "a", "PREREQUISITE", None)])
    assert prerequisite != related
    assert prerequisite != reversed_edge


def test_concept_creation_alone_is_not_recent_learning_activity():
    now = datetime(2026, 8, 27, tzinfo=UTC)
    concept = Concept(canonical_name="Passive Concept", created_at=now)

    untouched = _facts(concept, UserConcept(), now)
    active = _facts(concept, UserConcept(last_seen_at=now), now)

    assert untouched["recent"] is False
    assert untouched["recency"] == 0.0
    assert active["recent"] is True
    assert active["recency"] == 1.0


def test_portrait_activation_requires_ten_meaningful_interactions():
    assert has_portrait_evidence(9) is False
    assert has_portrait_evidence(10) is True


def test_review_attempt_is_counted_once_as_activity():
    now = datetime(2026, 8, 27, tzinfo=UTC)
    concept = Concept(canonical_name="Reviewed Concept")
    state = UserConcept(attempt_count=5, review_count=5, last_tested_at=now)

    assert _facts(concept, state, now)["interactions"] == 5


def test_changes_report_classifications_that_appear_or_recede():
    previous = {
        "emerging_threads": [],
        "frontiers": [{"name": "Operator Theory"}],
        "bridges": [],
    }
    current = SimpleNamespace(
        emerging_threads=[],
        frontiers=[SimpleNamespace(name="Functional Analysis")],
        bridges=[],
    )

    changes = _changes(previous, current)

    assert [(change.kind, change.text) for change in changes] == [
        ("frontier", "Frontier appeared: Functional Analysis"),
        ("frontier", "Frontier receded: Operator Theory"),
    ]


def test_algorithm_version_change_creates_a_new_snapshot(monkeypatch):
    now = datetime(2026, 8, 27, tzinfo=UTC)

    def model(input_hash: str, algorithm_version: str) -> PortraitModel:
        return PortraitModel(
            snapshot_id="old",
            generated_at=now,
            version=1,
            algorithm_version=algorithm_version,
            config_version="portrait-defaults-1",
            input_hash=input_hash,
            summary=PortraitSummary(
                concept_count=1, mastered_concept_count=0, domain_count=1, active_frontier_count=0
            ),
            narrative="still forming",
        )

    stored = model("old-hash", "portrait-1")
    current = model("new-hash", "portrait-2")
    latest = SimpleNamespace(payload={"frontiers": [], "bridges": [], "emerging_threads": []})

    class FakeSession:
        def __init__(self):
            self.added = []

        async def execute(self, _statement):
            return SimpleNamespace(scalar_one_or_none=lambda: latest)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

        async def commit(self):
            return None

    async def fake_build(_session, _user):
        return current

    async def identity(_session, value):
        return value

    monkeypatch.setattr(portrait_service, "build_portrait", fake_build)
    monkeypatch.setattr(portrait_service, "_stored_model", lambda _snapshot: stored)
    monkeypatch.setattr(portrait_service, "with_visual_sources", identity)

    session = FakeSession()
    result = asyncio.run(get_portrait(session, SimpleNamespace(id=uuid4())))

    assert len(session.added) == 1
    assert result.algorithm_version == "portrait-2"


def test_portrait_failure_rolls_back_before_serving_previous_snapshot(monkeypatch):
    stored = SimpleNamespace(snapshot_id="previous")
    latest = SimpleNamespace(payload={})

    class FakeSession:
        rolled_back = False

        async def execute(self, _statement):
            return SimpleNamespace(scalar_one_or_none=lambda: latest)

        async def rollback(self):
            self.rolled_back = True

    async def failed_build(_session, _user):
        raise RuntimeError("portrait failed")

    async def serve_previous(session, value):
        assert session.rolled_back
        return value

    monkeypatch.setattr(portrait_service, "build_portrait", failed_build)
    monkeypatch.setattr(portrait_service, "_stored_model", lambda _snapshot: stored)
    monkeypatch.setattr(portrait_service, "with_visual_sources", serve_previous)

    session = FakeSession()
    result = asyncio.run(get_portrait(session, SimpleNamespace(id=uuid4())))

    assert result is stored


def test_stored_portrait_can_be_served_without_recomputing(monkeypatch):
    stored = SimpleNamespace(snapshot_id="previous")
    latest = SimpleNamespace(payload={})

    class FakeSession:
        async def execute(self, _statement):
            return SimpleNamespace(scalar_one_or_none=lambda: latest)

    async def should_not_build(_session, _user):
        raise AssertionError("stored portrait reads must not rebuild")

    async def identity(_session, value):
        return value

    monkeypatch.setattr(portrait_service, "build_portrait", should_not_build)
    monkeypatch.setattr(portrait_service, "_stored_model", lambda _snapshot: stored)
    monkeypatch.setattr(portrait_service, "with_visual_sources", identity)

    result = asyncio.run(get_portrait(FakeSession(), SimpleNamespace(id=uuid4()), recompute=False))

    assert result is stored


def test_refresh_recompute_does_not_hide_build_failures(monkeypatch):
    latest = SimpleNamespace(payload={})

    class FakeSession:
        rolled_back = False

        async def execute(self, _statement):
            return SimpleNamespace(scalar_one_or_none=lambda: latest)

        async def rollback(self):
            self.rolled_back = True

    async def failed_build(_session, _user):
        raise RuntimeError("portrait failed")

    monkeypatch.setattr(portrait_service, "build_portrait", failed_build)
    session = FakeSession()

    with pytest.raises(RuntimeError, match="portrait failed"):
        asyncio.run(get_portrait(
            session, SimpleNamespace(id=uuid4()), recompute=True, fallback_on_error=False
        ))

    assert session.rolled_back


async def test_portrait_debug_reports_exact_emerging_thread_contributions():
    now = datetime(2026, 8, 27, tzinfo=UTC)
    pairs = [
        (Concept(id=uuid4(), canonical_name=name, domain="Formal Methods"), UserConcept(
            mastery_score=0, interest_score=50, attempt_count=4, review_count=4,
            last_tested_at=now,
        ))
        for name in ("Lean", "Types", "Verification")
    ]

    class Result:
        def __init__(self, values):
            self.values = values

        def all(self):
            return self.values

        def scalars(self):
            return SimpleNamespace(all=lambda: self.values)

    class Session:
        def __init__(self):
            self.results = iter((Result(pairs), Result([]), Result([]), Result([])))

        async def execute(self, _statement):
            return next(self.results)

    debug = []
    result = await build_portrait(Session(), SimpleNamespace(id=uuid4()), now=now, debug=debug)

    entry = next(item for item in debug if item["kind"] == "emerging_thread")
    assert entry["selected"] is True
    assert entry["score"] == result.emerging_threads[0].score
    assert [factor["name"] for factor in entry["factors"]] == [
        "recent concept ratio", "recent interaction ratio"
    ]
    assert sum(factor["contribution"] for factor in entry["factors"]) == entry["score"]


def test_anchor_score_rewards_mastery_and_reinforcement():
    assert anchor_score(0.9, 0.8, 0.8, 0.7) > anchor_score(0.9, 0.1, 0.1, 0.1)


def test_frontier_score_rewards_ready_recent_partial_mastery():
    assert frontier_score(0.8, 0.9, 1.0, 0.8, 0.4) > frontier_score(0.2, 0.1, 0, 0.1, 0.95)


def test_emerging_thread_requires_real_evidence():
    assert is_emerging_thread(3, 3)
    assert not is_emerging_thread(2, 5)
    assert not is_emerging_thread(5, 2)


def test_portrait_scoring_accepts_a_configuration_profile():
    config = PortraitConfig(anchor_weights=(1.0, 0.0, 0.0, 0.0), min_interactions=11)

    assert anchor_score(0.9, 0.1, 0.1, 0.1, config) == 0.9
    assert has_portrait_evidence(10, config) is False
    assert has_portrait_evidence(11, config) is True

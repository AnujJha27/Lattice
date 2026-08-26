from __future__ import annotations

import pytest

from app.domain.graph import ancestors, ensure_acyclic, topological_order

NODES = {"a", "b", "c", "d"}
EDGES = [("a", "b"), ("b", "c"), ("a", "c")]


class TestEnsureAcyclic:
    def test_valid_edge_passes(self):
        ensure_acyclic(NODES, EDGES, ("c", "d"))

    def test_self_edge_rejected(self):
        with pytest.raises(ValueError):
            ensure_acyclic(NODES, EDGES, ("a", "a"))

    def test_direct_cycle_rejected(self):
        with pytest.raises(ValueError):
            ensure_acyclic(NODES, EDGES, ("b", "a"))

    def test_long_cycle_rejected(self):
        chain = [("n1", "n2"), ("n2", "n3"), ("n3", "n4")]
        with pytest.raises(ValueError):
            ensure_acyclic({"n1", "n2", "n3", "n4"}, chain, ("n4", "n1"))


class TestTopologicalOrder:
    def test_respects_dependencies(self):
        order = topological_order(NODES, EDGES)
        pos = {n: i for i, n in enumerate(order)}
        assert pos["a"] < pos["b"] < pos["c"]
        assert len(order) == len(NODES)

    def test_cycle_detected(self):
        with pytest.raises(ValueError):
            topological_order({"x", "y"}, [("x", "y"), ("y", "x")])


class TestAncestors:
    def test_transitive_prerequisites(self):
        assert ancestors("c", EDGES) == {"a", "b"}

    def test_root_has_none(self):
        assert ancestors("a", EDGES) == set()

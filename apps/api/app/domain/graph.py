"""Prerequisite-graph algorithms operating on plain edge tuples.

Kept free of ORM/session concerns so it's trivially unit-testable.
The API layer validates every prerequisite insert through `ensure_acyclic`.
"""
from collections import defaultdict, deque


def ensure_acyclic(nodes: set[str], edges: list[tuple[str, str]], candidate: tuple[str, str]) -> None:
    """Raise ValueError if adding candidate edge (a→b) creates a cycle."""
    src, dst = candidate
    if src == dst:
        raise ValueError("A concept cannot be its own prerequisite")
    adjacency = _adjacency(edges)
    # Cycle exists iff dst already reaches src.
    seen: set[str] = set()
    queue = deque([dst])
    while queue:
        node = queue.popleft()
        if node == src:
            raise ValueError(
                f"Prerequisite edge {src} -> {dst} would create a cycle"
            )
        for nxt in adjacency.get(node, ()):  # noqa: B905 — zip not needed
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)


def topological_order(nodes: set[str], edges: list[tuple[str, str]]) -> list[str]:
    """Kahn's algorithm; raises on cycles."""
    adjacency = _adjacency(edges)
    indegree = {n: 0 for n in nodes}
    for _, dst in edges:
        indegree[dst] += 1
    queue = deque(sorted(n for n, d in indegree.items() if d == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(adjacency.get(node, ())):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(nodes):
        raise ValueError("Graph contains a cycle")
    return order


def ancestors(node: str, edges: list[tuple[str, str]]) -> set[str]:
    """All prerequisites reachable from `node`."""
    reverse = defaultdict(set)
    for src, dst in edges:
        reverse[dst].add(src)
    seen: set[str] = set()
    queue = deque([node])
    while queue:
        current = queue.popleft()
        for parent in reverse.get(current, ()):
            if parent not in seen:
                seen.add(parent)
                queue.append(parent)
    return seen


def _adjacency(edges: list[tuple[str, str]]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for src, dst in edges:
        adjacency[src].add(dst)
    return dict(adjacency)

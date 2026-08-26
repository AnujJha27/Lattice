"""Deterministic source ranking (overrides §16).

    S(s) = w_a·A(s) + w_r·R(s) + w_f·F(s) + w_p·P(s)

Weights vary by domain policy: freshness is near-worthless for pure math,
crucial for API documentation. Every factor is logged so rankings are
debuggable (spec §19).
"""
from dataclasses import dataclass
from datetime import date

from app.modules.sources.schemas import SourceCandidate


@dataclass
class DomainPolicy:
    name: str = "general"
    w_authority: float = 0.45
    w_relevance: float = 0.35
    w_freshness: float = 0.1
    w_primary: float = 0.1


# Domain-specific policies — extend as domains are encountered.
POLICIES: dict[str, DomainPolicy] = {
    "mathematics": DomainPolicy("mathematics", w_authority=0.5, w_relevance=0.35, w_freshness=0.02, w_primary=0.13),
    "physics": DomainPolicy("physics", w_authority=0.45, w_relevance=0.32, w_freshness=0.08, w_primary=0.15),
    "computer science": DomainPolicy(
        "computer science", w_authority=0.42, w_relevance=0.33, w_freshness=0.17, w_primary=0.08
    ),
    "medicine": DomainPolicy("medicine", w_authority=0.55, w_relevance=0.3, w_freshness=0.1, w_primary=0.05),
    "history": DomainPolicy("history", w_authority=0.5, w_relevance=0.33, w_freshness=0.02, w_primary=0.15),
}


def policy_for_domain(domain: str | None) -> DomainPolicy:
    if not domain:
        return DomainPolicy()
    key = domain.strip().lower()
    for name, policy in POLICIES.items():
        if name in key or key in name:
            return policy
    return DomainPolicy()


def relevance_score(candidate: SourceCandidate, query: str) -> float:
    """Cheap lexical overlap between query terms and title+snippet (0..1)."""
    text = f"{candidate.title} {candidate.snippet}".lower()
    query_terms = [t for t in query.lower().split() if len(t) > 2]
    if not query_terms:
        return 0.5
    hits = sum(1 for term in query_terms if term in text)
    provider_score = candidate.extra.get("score")
    base = hits / len(query_terms)
    if isinstance(provider_score, int | float):
        # Tavily's 0..1 similarity blends in at low weight.
        base = 0.7 * base + 0.3 * float(provider_score)
    return min(base, 1.0)


def freshness_score(published: date | None) -> float:
    """Exponential decay over ~4 years; undated sources get a neutral 0.5."""
    if published is None:
        return 0.5
    age_years = max((date.today() - published).days / 365.25, 0)
    return 2 ** (-age_years / 2)


def primary_preference(candidate: SourceCandidate) -> float:
    """Primary-source preference from provider metadata."""
    extra_type = candidate.extra.get("source_type")
    score_map = {
        "paper": 1.0,
        "docs": 0.9,
        "textbook": 0.8,
        "reference": 0.5,
        "blog": 0.2,
        "forum": 0.1,
    }
    return score_map.get(str(extra_type), 0.5)


def rank_candidates(
    candidates: list[SourceCandidate],
    query: str,
    policy: DomainPolicy | None = None,
) -> list[tuple[SourceCandidate, dict]]:
    """Return candidates sorted by composite score, each with its factor breakdown."""
    policy = policy or DomainPolicy()
    scored: list[tuple[SourceCandidate, dict]] = []

    for c in candidates:
        factors = {
            "authority": round(c.authority, 3),
            "relevance": round(relevance_score(c, query), 3),
            "freshness": round(freshness_score(c.published), 3),
            "primary": round(primary_preference(c), 3),
        }
        total = (
            policy.w_authority * factors["authority"]
            + policy.w_relevance * factors["relevance"]
            + policy.w_freshness * factors["freshness"]
            + policy.w_primary * factors["primary"]
        )
        factors["total"] = round(total, 4)
        factors["policy"] = policy.name
        scored.append((c, factors))

    scored.sort(key=lambda pair: pair[1]["total"], reverse=True)
    return scored

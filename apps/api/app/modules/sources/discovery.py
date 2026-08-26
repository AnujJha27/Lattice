"""Source discovery orchestration.

Fans out to all configured WebSearchProviders, normalizes hits into
candidates, dedupes, then ranks deterministically (overrides §12-13).
"""
import logging

from app.core.config import get_settings
from app.modules.sources.classify import classify_source
from app.modules.sources.dedup import dedupe_candidates
from app.modules.sources.ranking import policy_for_domain, rank_candidates
from app.modules.sources.schemas import RankedCandidate, SourceCandidate

logger = logging.getLogger(__name__)


def _publisher_from_url(url: str) -> str | None:
    """Derive a display publisher from the hostname (www stripped, TLD trimmed)."""
    from urllib.parse import urlparse

    host = urlparse(url).hostname or ""
    host = host.removeprefix("www.")
    parts = host.split(".")
    if len(parts) <= 1:
        return None
    core = ".".join(parts[:-1])  # drop TLD (crude for .co.uk — acceptable)
    return core.split(".")[0].replace("-", " ").title() or None


def _providers():
    settings = get_settings()
    providers = []

    if settings.tavily_api_key:
        from app.providers.tavily import TavilySearchProvider

        providers.append(TavilySearchProvider(settings.tavily_api_key))

    from app.providers.arxiv import ArxivProvider
    from app.providers.openalex import OpenAlexProvider

    providers.append(ArxivProvider())
    providers.append(OpenAlexProvider())
    return providers


async def discover(query: str, domain: str | None, limit: int) -> tuple[list[RankedCandidate], int]:
    """Returns (ranked candidates, raw hit count before dedup)."""
    candidates: list[SourceCandidate] = []
    per_provider_limit = max(limit, 8)

    for provider in _providers():
        try:
            hits = await provider.search(query, limit=per_provider_limit)
        except Exception:  # noqa: BLE001 — one failing provider must not kill discovery
            logger.exception("search provider %s failed", provider.provider_name)
            continue
        for hit in hits:
            if not hit.url or not hit.title:
                continue
            source_type, authority = classify_source(hit.url)
            extra = dict(hit.extra)
            if source_type.value == "ACADEMIC_PAPER":
                extra.setdefault("source_type", "paper")
            publisher = _publisher_from_url(str(hit.url))
            candidates.append(
                SourceCandidate(
                    title=hit.title[:300],
                    url=str(hit.url),
                    snippet=hit.snippet[:600],
                    published=hit.published,
                    provider=hit.provider,
                    source_type=source_type.value,
                    authority=authority,
                    publisher=publisher,
                    doi=extra.get("doi"),
                    arxiv_id=extra.get("arxiv_id"),
                    authors=[a for a in extra.get("authors", []) if a][:10],
                    extra=extra,
                )
            )

    unique, dropped = dedupe_candidates(candidates)
    policy = policy_for_domain(domain)
    ranked = rank_candidates(unique, query, policy)

    return (
        [RankedCandidate(candidate=c, factors=f) for c, f in ranked[:limit]],
        len(candidates),
    )

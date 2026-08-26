"""Source deduplication (overrides §15).

Priority keys: DOI > arXiv ID > normalized canonical URL. Content-hash dedup
happens at ingest time.
"""
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "ref_src", "fbclid", "gclid", "mc_cid", "mc_eid",
}


def canonicalize_url(url: str) -> str:
    """Stable canonical form: lowercase host, drop tracking params/trailing slash."""
    parsed = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in STRIP_PARAMS]
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.hostname or "", path, "", urlencode(query), ""))


def dedupe_key(doi: str | None, arxiv_id: str | None, url: str | None) -> str:
    if doi:
        return f"doi:{doi.strip().lower()}"
    if arxiv_id:
        return f"arxiv:{arxiv_id.strip().lower()}"
    if url:
        return f"url:{canonicalize_url(url)}"
    raise ValueError("A source needs at least one of doi / arxiv_id / url")


def dedupe_candidates(candidates: list) -> tuple[list, int]:
    """Keep the first occurrence per key. Returns (unique, dropped_count)."""
    seen: set[str] = set()
    unique = []
    for candidate in candidates:
        key = dedupe_key(candidate.doi, candidate.arxiv_id, candidate.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique, len(candidates) - len(unique)

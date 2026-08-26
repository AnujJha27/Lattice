"""URL → source classification and authority heuristics.

Deterministic, domain-aware (overrides §8-11). The trust hierarchy is encoded
here: official docs, standards bodies, academia and primary sources outrank
blogs/forums. Wikipedia is a good index but demoted as a lesson foundation.
"""
from urllib.parse import urlparse

from app.db.models.source import SourceType

# Base authority by type — 0..1
TYPE_AUTHORITY: dict[SourceType, float] = {
    SourceType.OFFICIAL_DOCUMENTATION: 0.95,
    SourceType.STANDARDS_BODY: 0.97,
    SourceType.TEXTBOOK: 0.92,
    SourceType.ACADEMIC_PAPER: 0.9,
    SourceType.UNIVERSITY_MATERIAL: 0.85,
    SourceType.GOVERNMENT: 0.85,
    SourceType.PRIMARY_SOURCE: 0.8,
    SourceType.REFERENCE_WORK: 0.7,
    SourceType.HIGH_QUALITY_EXPLAINER: 0.6,
    SourceType.NEWS: 0.5,
    SourceType.BLOG: 0.35,
    SourceType.FORUM: 0.25,
    SourceType.USER_SOURCE: 0.5,  # owned by user; neutral default
    SourceType.OTHER: 0.4,
}

ACADEMIC_HOSTS = {"arxiv.org", "openalex.org", "semanticscholar.org", "jstor.org", "acm.org", "ieee.org"}
STANDARDS_HOSTS = {"w3.org", "ietf.org", "rfc-editor.org", "iso.org", "whatwg.org", "ecma-international.org"}
GOV_TLDS = {".gov", ".gov.uk", ".gov.au", ".gov.in", ".europa.eu"}
EDU_TLDS = {".edu", ".edu.au", ".edu.in", ".ac.uk"}

DOC_HINTS = ("docs.", "developer.", "documentation", "/docs", "learn.", "reference.")


def classify_source(url: str) -> tuple[SourceType, float]:
    """Return (source_type, authority in 0..1) for a URL."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return SourceType.OTHER, TYPE_AUTHORITY[SourceType.OTHER]

    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()

    if any(host == d or host.endswith("." + d) for d in ACADEMIC_HOSTS):
        st = SourceType.ACADEMIC_PAPER
        boost = 0.05 if "arxiv" in host else 0.0
        return st, min(TYPE_AUTHORITY[st] + boost, 1.0)

    if any(host == d or host.endswith("." + d) for d in STANDARDS_HOSTS):
        st = SourceType.STANDARDS_BODY
        return st, TYPE_AUTHORITY[st]

    if any(host.endswith(tld) or host == tld.lstrip(".") for tld in GOV_TLDS):
        return SourceType.GOVERNMENT, TYPE_AUTHORITY[SourceType.GOVERNMENT]

    if any(host.endswith(tld) for tld in EDU_TLDS):
        if "ocw" in host or "course" in path or "lecture" in path:
            return SourceType.UNIVERSITY_MATERIAL, TYPE_AUTHORITY[SourceType.UNIVERSITY_MATERIAL]
        return SourceType.UNIVERSITY_MATERIAL, TYPE_AUTHORITY[SourceType.UNIVERSITY_MATERIAL] - 0.05

    if host == "wikipedia.org" or host.endswith(".wikipedia.org"):
        return SourceType.REFERENCE_WORK, TYPE_AUTHORITY[SourceType.REFERENCE_WORK]

    if any(hint in host or hint in path for hint in DOC_HINTS):
        return SourceType.OFFICIAL_DOCUMENTATION, TYPE_AUTHORITY[SourceType.OFFICIAL_DOCUMENTATION]

    if any(h in host for h in ("reddit.com", "stackoverflow.com", "news.ycombinator.com", "quora.com")):
        return SourceType.FORUM, TYPE_AUTHORITY[SourceType.FORUM]

    if "medium.com" in host or "substack.com" in host or "dev.to" in host:
        return SourceType.BLOG, TYPE_AUTHORITY[SourceType.BLOG]

    return SourceType.OTHER, TYPE_AUTHORITY[SourceType.OTHER]

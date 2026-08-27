"""OpenAlex — free scholarly metadata index (~250M works).

Great for authority signals, DOI resolution, citation counts.
"""
import re
from datetime import datetime

import httpx

from app.providers.search import SearchHit


class OpenAlexProvider:
    provider_name = "openalex"
    endpoint = "https://api.openalex.org/works"

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        # OpenAlex's query parser 400s on punctuation like "?" — strip it.
        clean = " ".join(re.sub(r"[^\w\s-]", "", query).split())
        params = {"search": clean, "per-page": limit}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(self.endpoint, params=params)
            resp.raise_for_status()
            data = resp.json()
        hits: list[SearchHit] = []
        for work in data.get("results", []):
            published_raw = work.get("publication_date")
            primary = (work.get("primary_location") or {}).get("landing_page_url")
            doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
            open_access_url = _open_access_url(work)
            hits.append(
                SearchHit(
                    title=work.get("title") or "",
                    url=open_access_url or primary or work.get("doi") or "",
                    snippet=(work.get("abstract_inverted_index") is not None and "") or "",
                    published=(
                        datetime.strptime(published_raw, "%Y-%m-%d").date()
                        if published_raw else None
                    ),
                    provider=self.provider_name,
                    extra={
                        "doi": doi,
                        "openalex_id": work.get("id"),
                        "cited_by_count": work.get("cited_by_count"),
                        "authors": [
                            a["author"]["display_name"]
                            for a in work.get("authorships", [])[:10]
                        ],
                    },
                )
            )
        return hits


def _open_access_url(work: dict) -> str | None:
    locations = [work.get("best_oa_location"), *(work.get("locations") or [])]
    for location in locations:
        if not isinstance(location, dict):
            continue
        for key in ("pdf_url", "landing_page_url"):
            url = location.get(key)
            if isinstance(url, str) and url.startswith("https://"):
                return url
    return None

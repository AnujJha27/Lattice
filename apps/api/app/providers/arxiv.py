"""arXiv API search — free, authoritative for academic preprints.

Uses the Atom API. Rate limit: be polite (~1 req / 3s sustained).
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from app.providers.search import SearchHit

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_ID_RE = re.compile(r"abs/([\w.\-/]+?)(?:v\d+)?$")


class ArxivProvider:
    provider_name = "arxiv"
    endpoint = "https://export.arxiv.org/api/query"

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(self.endpoint, params=params)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        hits: list[SearchHit] = []
        for entry in root.findall(f"{ATOM}entry"):
            url = (entry.findtext(f"{ATOM}id") or "").strip()
            match = ARXIV_ID_RE.search(url)
            published_raw = entry.findtext(f"{ATOM}published")
            hits.append(
                SearchHit(
                    title=" ".join((entry.findtext(f"{ATOM}title") or "").split()),
                    url=url,
                    snippet=" ".join((entry.findtext(f"{ATOM}summary") or "").split())[:500],
                    published=(
                        datetime.fromisoformat(published_raw.replace("Z", "+00:00")).date()
                        if published_raw else None
                    ),
                    provider=self.provider_name,
                    extra={"arxiv_id": match.group(1) if match else None,
                           "authors": [a.findtext(f"{ATOM}name") for a in entry.findall(f"{ATOM}author")]},
                )
            )
        return hits

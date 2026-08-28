"""Tavily web-search implementation (free tier: ~1k queries/month)."""
import httpx

from app.providers.search import SearchHit

MAX_RAW_CONTENT_CHARS = 100_000


class TavilySearchProvider:
    provider_name = "tavily"
    endpoint = "https://api.tavily.com/search"
    extract_endpoint = "https://api.tavily.com/extract"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "query": query,
                    "max_results": limit,
                    "include_raw_content": True,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        hits = []
        for item in data.get("results", []):
            extra = {"score": item.get("score")}
            raw_content = item.get("raw_content")
            if isinstance(raw_content, str):
                extra["raw_content"] = raw_content[:MAX_RAW_CONTENT_CHARS]
            hits.append(
                SearchHit(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                    published=None,
                    provider=self.provider_name,
                    extra=extra,
                )
            )
        return hits

    async def extract(self, url: str) -> str | None:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.extract_endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"urls": url, "extract_depth": "basic"},
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        if not isinstance(results, list) or not results or not isinstance(results[0], dict):
            return None
        raw_content = results[0].get("raw_content")
        return raw_content[:MAX_RAW_CONTENT_CHARS] if isinstance(raw_content, str) else None

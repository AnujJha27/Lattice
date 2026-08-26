"""Tavily web-search implementation (free tier: ~1k queries/month)."""
import httpx

from app.providers.search import SearchHit


class TavilySearchProvider:
    provider_name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str):
        self._api_key = api_key

    async def search(self, query: str, *, limit: int = 8) -> list[SearchHit]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                self.endpoint,
                json={"api_key": self._api_key, "query": query, "max_results": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            SearchHit(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "")[:500],
                published=None,
                provider=self.provider_name,
                extra={"score": item.get("score")},
            )
            for item in data.get("results", [])
        ]

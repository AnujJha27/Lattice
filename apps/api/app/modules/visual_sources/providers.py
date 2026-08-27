"""Small provider adapter for openly licensed Wikimedia Commons metadata."""
from urllib.parse import quote

import httpx

from app.modules.visual_sources.ranking import VisualAssetCandidate
from app.modules.visual_sources.rights import RightsClass, classify_license


class WikimediaProvider:
    name = "Wikimedia Commons"
    endpoint = "https://commons.wikimedia.org/w/api.php"

    async def search(self, query: str, limit: int = 8) -> list[VisualAssetCandidate]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",
            "gsrlimit": min(limit, 20),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size",
            "iiurlwidth": 1000,
            "format": "json",
            "origin": "*",
        }
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {}).values()
        candidates = []
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            metadata = info.get("extmetadata") or {}
            license_name = _metadata_value(metadata, "LicenseShortName")
            rights_class = classify_license(license_name)
            title = str(page.get("title", "")).removeprefix("File:")
            image_url = info.get("thumburl") or info.get("url")
            if not title or not image_url:
                continue
            width = _int(info.get("thumbwidth") or info.get("width"))
            height = _int(info.get("thumbheight") or info.get("height"))
            quality = min(1.0, ((width or 0) * (height or 0)) / 1_500_000) if width and height else 0.35
            rights_score = {"PUBLIC_DOMAIN": 1.0, "CC0": 1.0, "CC_BY": 0.9, "CC_BY_SA": 0.75}.get(rights_class.value, 0.0)
            candidates.append(VisualAssetCandidate(
                title=title[:500],
                canonical_url=f"https://commons.wikimedia.org/wiki/{quote(str(page.get('title', '')).replace(' ', '_'))}",
                image_url=str(image_url),
                thumbnail_url=str(info.get("thumburl")) if info.get("thumburl") else None,
                rights_class=rights_class,
                relevance_score=_text_relevance(query, title),
                aesthetic_score=0.6,
                rights_score=rights_score,
                quality_score=quality,
                creator=_metadata_value(metadata, "Artist"),
                date=_metadata_value(metadata, "DateTimeOriginal") or _metadata_value(metadata, "DateTime"),
                license=license_name,
                attribution_text=_metadata_value(metadata, "Credit") or _metadata_value(metadata, "Artist"),
                width=width,
                height=height,
                provider=self.name,
            ))
        return candidates


class MetProvider:
    """Fallback adapter for The Met's public-domain Open Access collection."""

    name = "The Metropolitan Museum of Art"
    endpoint = "https://collectionapi.metmuseum.org/public/collection/v1"

    async def search(self, query: str, limit: int = 8) -> list[VisualAssetCandidate]:
        params = {"q": query, "hasImages": "true", "isPublicDomain": "true"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(f"{self.endpoint}/search", params=params)
            response.raise_for_status()
            object_ids = (response.json().get("objectIDs") or [])[: min(max(limit, 0), 10)]
            candidates = []
            for object_id in object_ids:
                try:
                    object_response = await client.get(f"{self.endpoint}/objects/{object_id}")
                    object_response.raise_for_status()
                except httpx.HTTPError:
                    continue
                record = object_response.json()
                if record.get("isPublicDomain") is not True:
                    continue
                title = str(record.get("title") or "").strip()
                image_url = str(record.get("primaryImage") or "").strip()
                if not title or not image_url.startswith("https://"):
                    continue
                canonical_url = str(record.get("objectURL") or "").strip()
                if not canonical_url.startswith("https://"):
                    canonical_url = f"https://www.metmuseum.org/art/collection/search/{object_id}"
                candidates.append(VisualAssetCandidate(
                    title=title[:500], canonical_url=canonical_url, image_url=image_url,
                    thumbnail_url=str(record.get("primaryImageSmall") or image_url),
                    rights_class=RightsClass.PUBLIC_DOMAIN,
                    relevance_score=_text_relevance(query, title), aesthetic_score=0.6,
                    rights_score=1.0, quality_score=0.65,
                    creator=str(record.get("artistDisplayName") or "").strip() or None,
                    institution=self.name, date=str(record.get("objectDate") or "").strip() or None,
                    license="Public Domain",
                    attribution_text=f"{self.name}, Open Access",
                    provider=self.name,
                ))
        return candidates


def _metadata_value(metadata: dict, key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return str(value).strip()[:1000] if value else None


def _int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _text_relevance(query: str, title: str) -> float:
    query_words = {word.casefold() for word in query.split() if len(word) > 2}
    title_words = {word.casefold().strip(".,:;()[]") for word in title.split()}
    return min(1.0, 0.35 + 0.65 * len(query_words & title_words) / max(1, len(query_words)))

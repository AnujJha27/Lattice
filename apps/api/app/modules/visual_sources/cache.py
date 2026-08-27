"""Bounded caching for rights-cleared visual bytes."""
from dataclasses import dataclass
from hashlib import sha256

import httpx

from app.providers.storage import ObjectStorageProvider

MAX_IMAGE_BYTES = 8_000_000


@dataclass(frozen=True)
class CachedImage:
    key: str
    content_hash: str
    content_type: str


async def cache_image(url: str, storage: ObjectStorageProvider) -> CachedImage | None:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if not content_type.startswith("image/"):
                    return None
                chunks = []
                total = 0
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_IMAGE_BYTES:
                        return None
                    chunks.append(chunk)
    except httpx.HTTPError:
        return None

    data = b"".join(chunks)
    if not data:
        return None
    content_hash = sha256(data).hexdigest()
    key = f"visuals/{content_hash}"
    await storage.put(key, data, content_type)
    return CachedImage(key=key, content_hash=content_hash, content_type=content_type)

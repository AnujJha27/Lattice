from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx


class ObjectStorageProvider(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes under key; returns the storage key."""
        ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str: ...


class LocalStorageProvider:
    """Development implementation writing under ./data/storage."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("..", "_").lstrip("/")
        return self.root / safe

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass

    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str:
        # Dev only: local path placeholder. Real impl uses presigned URLs.
        _ = ttl_seconds
        return f"/storage/{self._path(key)}"


class SupabaseStorageProvider:
    """Private object storage backed by the Supabase Storage REST API."""

    def __init__(self, url: str, service_role_key: str, bucket: str):
        self.base_url = f"{url.rstrip('/')}/storage/v1"
        self.headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        }
        self.bucket = quote(bucket, safe="")

    def _object_url(self, key: str) -> str:
        return f"{self.base_url}/object/{self.bucket}/{quote(key, safe='/')}"

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        headers = {**self.headers, "Content-Type": content_type, "x-upsert": "true"}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(self._object_url(key), content=data, headers=headers)
            response.raise_for_status()
        return key

    async def get(self, key: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self._object_url(key), headers=self.headers)
            response.raise_for_status()
        return response.content

    async def delete(self, key: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.request(
                "DELETE",
                f"{self.base_url}/object/{self.bucket}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"prefixes": [key]},
            )
            response.raise_for_status()

    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/object/sign/{self.bucket}/{quote(key, safe='/')}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"expiresIn": ttl_seconds},
            )
            response.raise_for_status()
        signed = response.json().get("signedURL")
        if not isinstance(signed, str):
            raise RuntimeError("Supabase did not return a signed URL")
        return f"{self.base_url}{signed}" if signed.startswith("/") else signed


def make_storage() -> ObjectStorageProvider:
    from app.core.config import get_settings
    settings = get_settings()
    if settings.is_production:
        if not settings.supabase_service_role_key or "your-project" in settings.supabase_url:
            raise RuntimeError("Configure Supabase private storage for production")
        return SupabaseStorageProvider(
            settings.supabase_url,
            settings.supabase_service_role_key,
            settings.supabase_storage_bucket,
        )
    return LocalStorageProvider(Path("data/storage"))

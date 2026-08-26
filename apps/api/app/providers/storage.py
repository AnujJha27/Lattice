from pathlib import Path
from typing import Protocol


class ObjectStorageProvider(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str:
        """Store bytes under key; returns the storage key."""
        ...

    async def get(self, key: str) -> bytes: ...

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

    async def signed_url(self, key: str, ttl_seconds: int = 3600) -> str:
        # Dev only: local path placeholder. Real impl uses presigned URLs.
        _ = ttl_seconds
        return f"/storage/{self._path(key)}"


def make_storage() -> ObjectStorageProvider:
    from app.core.config import get_settings
    if get_settings().is_production:
        raise RuntimeError("Configure an S3-compatible storage provider for production")
    return LocalStorageProvider(Path("data/storage"))

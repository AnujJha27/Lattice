"""Small shared helper for rotating Google API keys on quota errors."""
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")
ClientFactory = Callable[[str], Any]


def is_quota_error(exc: Exception) -> bool:
    code = (
        getattr(exc, "status_code", None)
        or getattr(exc, "code", None)
        or getattr(exc, "status", None)
    )
    message = str(exc).casefold()
    return str(code) == "429" or "429" in message or "resource_exhausted" in message


def is_key_unavailable_error(exc: Exception) -> bool:
    """Allow another configured project key to handle a disabled project."""
    return is_quota_error(exc) or "service_disabled" in str(exc).casefold()


class GoogleKeyRotation:
    """Try each configured key once, then stick to the successful key."""

    def __init__(self, keys: list[str], client_factory: ClientFactory):
        self._keys = tuple(dict.fromkeys(key.strip() for key in keys if key.strip()))
        if not self._keys:
            raise RuntimeError("No Google API key configured")
        self._client_factory = client_factory
        self._current = 0
        self._clients: dict[int, Any] = {}

    def _client(self, index: int) -> Any:
        if index not in self._clients:
            self._clients[index] = self._client_factory(api_key=self._keys[index])
        return self._clients[index]

    async def call(self, operation: Callable[[Any], Awaitable[T]]) -> T:
        last_error: Exception | None = None
        for offset in range(len(self._keys)):
            index = (self._current + offset) % len(self._keys)
            try:
                result = await operation(self._client(index))
            except Exception as exc:
                if not is_key_unavailable_error(exc) or offset == len(self._keys) - 1:
                    raise
                last_error = exc
                continue
            self._current = index
            return result
        assert last_error is not None
        raise last_error

    async def stream(self, operation: Callable[[Any], AsyncIterator[T]]) -> AsyncIterator[T]:
        for offset in range(len(self._keys)):
            index = (self._current + offset) % len(self._keys)
            yielded = False
            try:
                async for item in operation(self._client(index)):
                    yielded = True
                    yield item
            except Exception as exc:
                if not is_key_unavailable_error(exc) or yielded or offset == len(self._keys) - 1:
                    raise
                continue
            self._current = index
            return

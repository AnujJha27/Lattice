import pytest
from starlette.requests import Request

from app.middleware import RequestContextMiddleware


@pytest.mark.asyncio
async def test_request_logging_preserves_unhandled_handler_error():
    request = Request({
        "type": "http",
        "method": "GET",
        "path": "/boom",
        "headers": [],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("127.0.0.1", 1),
    })

    async def fail(_request):
        raise RuntimeError("handler failed")

    with pytest.raises(RuntimeError, match="handler failed"):
        await RequestContextMiddleware(None).dispatch(request, fail)

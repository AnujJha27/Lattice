"""Stable error schema for every failure the API can produce.

Clients always receive: { error: { code, message }, request_id }.
Internal details never leak to responses in production.
"""
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings


class AppError(Exception):
    """Domain-level error with a stable machine-readable code."""

    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, code: str, message: str, status_code: int | None = None):
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class NotFound(AppError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, entity: str, id_: object):
        super().__init__("not_found", f"{entity} '{id_}' was not found")


class Forbidden(AppError):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, message: str = "You do not have access to this resource"):
        super().__init__("forbidden", message)


def _payload(request: Request, code: str, message: str, http_status: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message}, "request_id": request_id},
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _payload(request, exc.code, exc.message, exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _payload(request, "http_error", str(exc.detail), exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = f"Invalid value for '{loc}': {first.get('msg', 'validation failed')}"
        return _payload(request, "validation_error", msg, status.HTTP_422_UNPROCESSABLE_ENTITY)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger(__name__).exception("Unhandled exception", extra={"path": request.url.path})
        message = (
            "An unexpected error occurred" if get_settings().is_production else repr(exc)
        )
        return _payload(request, "internal_error", message, status.HTTP_500_INTERNAL_SERVER_ERROR)

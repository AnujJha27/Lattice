"""Lattice API entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(get_settings().log_level)
    from app.db.session import init_engine
    from app.jobs.runner import start_worker

    init_engine()
    worker = start_worker()
    yield
    worker.cancel()
    from app.db.session import engine

    if engine is not None:
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Lattice API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
    )
    origins = [o.strip() for o in settings.web_origin.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["authorization", "content-type"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

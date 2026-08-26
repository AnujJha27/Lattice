"""Async engine and session management for PostgreSQL."""
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def create_db_engine():
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.environment == "development" and False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


engine = None  # created lazily so importing the app never opens sockets
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global engine, session_factory
    if engine is None:
        engine = create_db_engine()
        session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async session per request."""
    init_engine()
    assert session_factory is not None
    async with session_factory() as session:
        yield session

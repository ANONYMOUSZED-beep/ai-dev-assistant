"""Async database engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings
from app.db.base import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _prepare(url: str) -> tuple[str, dict[str, object]]:
    """Normalise a DB URL for asyncpg and derive connect args.

    Managed Postgres (e.g. Neon) hands out libpq-style URLs with ``sslmode`` /
    ``channel_binding`` query params that asyncpg rejects. We strip those and
    enable TLS via ``connect_args`` for non-local hosts.
    """
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    # Tolerate pasting Neon's `psql '<url>'` command form (prefix + quotes).
    url = url.strip()
    if url.lower().startswith("psql"):
        url = url[4:].strip()
    url = url.strip("'\"").strip()

    if url.startswith("sqlite"):
        return url, {}

    parts = urlsplit(url)
    # Managed providers hand out libpq scheme (postgres:// or postgresql://).
    # SQLAlchemy's async engine needs the asyncpg driver explicitly.
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if k not in ("sslmode", "channel_binding")
    ]
    clean = urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment)
    )
    connect_args: dict[str, object] = {}
    if (parts.hostname or "") not in ("localhost", "127.0.0.1", ""):
        connect_args["ssl"] = True  # managed Postgres requires TLS
    return clean, connect_args


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        settings = settings or get_settings()
        url, connect_args = _prepare(settings.async_database_url)
        _engine = create_async_engine(
            url,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


async def init_db() -> None:
    """Create tables for all registered models (dev convenience / first run)."""
    # Import models so they register on the metadata before create_all.
    from app.db import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_db() -> None:
    """Dispose the engine on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional async session."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

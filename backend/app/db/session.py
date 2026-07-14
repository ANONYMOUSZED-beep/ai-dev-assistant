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


def get_sync_dsn(settings: Settings | None = None) -> str:
    """Return a libpq DSN (for psycopg2 / pgvector) from the configured DB URL.

    Uses the plain ``postgresql://`` scheme (no async driver) and ensures TLS for
    managed hosts, tolerating the same ``psql '...'`` paste form as the async URL.
    """
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    settings = settings or get_settings()
    url = settings.async_database_url.strip()
    if url.lower().startswith("psql"):
        url = url[4:].strip()
    url = url.strip("'\"").strip()

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    host = parts.hostname or ""
    if host not in ("localhost", "127.0.0.1", "") and "sslmode" not in query:
        query["sslmode"] = "require"
    return urlunsplit(
        ("postgresql", parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


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
    """Create tables for all registered models (dev convenience / first run).

    Also applies a few additive column migrations for tables that predate newer
    columns. ``create_all`` only creates *missing* tables — it never alters an
    existing one — so on a database where ``conversations`` already exists we add
    the newer columns idempotently.
    """
    # Import models so they register on the metadata before create_all.
    from app.db import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _apply_additive_migrations(conn)


# Additive, idempotent column migrations keyed by dialect. PostgreSQL supports
# ``ADD COLUMN IF NOT EXISTS`` natively; SQLite (used in tests) always gets a fresh
# schema from create_all, so migrations there are unnecessary and skipped.
_PG_MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS kind VARCHAR(16) DEFAULT 'docs'",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS repository_id VARCHAR(36)",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS share_id VARCHAR(64)",
    # Google sign-in: users may have no local password, plus email/subject columns.
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(320)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255)",
    "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
)


async def _apply_additive_migrations(conn: object) -> None:
    """Run additive column migrations on PostgreSQL; no-op elsewhere."""
    from sqlalchemy import text

    dialect = getattr(getattr(conn, "engine", None), "dialect", None)
    dialect_name = getattr(dialect, "name", "")
    if dialect_name != "postgresql":
        return
    for statement in _PG_MIGRATIONS:
        try:
            await conn.execute(text(statement))  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - depends on live DB
            from app.core.logging import get_logger

            get_logger(__name__).warning("Migration skipped (%s): %s", statement, exc)


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

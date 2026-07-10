"""Liveness / readiness endpoints.

``/health`` is a liveness probe (is the process up?) and always returns 200.
``/health/ready`` is a readiness probe (are dependencies reachable?) and returns
503 when a required dependency is down, so orchestrators route traffic correctly.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.cache.redis import get_redis
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, object]:
    """Liveness probe with a best-effort Redis check (always 200)."""
    settings = get_settings()
    redis_ok = False
    try:
        redis_ok = bool(await get_redis().ping())
    except Exception:  # pragma: no cover - depends on live redis
        redis_ok = False

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "vector_store": settings.vector_store,
        "redis": "up" if redis_ok else "down",
    }


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """Readiness probe: verifies Redis and the database are reachable."""
    checks: dict[str, bool] = {}

    try:
        checks["redis"] = bool(await get_redis().ping())
    except Exception:  # pragma: no cover - depends on live redis
        checks["redis"] = False

    try:
        from app.db.session import get_sessionmaker

        async with get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:  # pragma: no cover - depends on live database
        checks["database"] = False

    ready = all(checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not_ready", "checks": checks},
    )

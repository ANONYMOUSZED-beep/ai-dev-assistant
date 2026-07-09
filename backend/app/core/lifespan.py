"""Application lifespan: construct shared engines and initialise infrastructure."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import dispose_db, init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build engines on startup; dispose resources on shutdown.

    Heavy engine construction is imported lazily so that importing the app (e.g. in
    tooling or tests with dependency overrides) does not require model downloads.
    """
    settings = get_settings()
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)

    if settings.is_production and not settings.auth_enabled:
        logger.warning(
            "Running in production with NO API keys configured — all endpoints "
            "are unauthenticated. Set API_KEYS to enable authentication."
        )

    # Lazy imports keep module import light-weight and side-effect free.
    from app.llm.factory import get_llm_provider
    from app.rag.pipeline import RagPipeline

    try:
        await init_db()
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.warning("Database initialisation skipped: %s", exc)

    # Build engines defensively: a failure here must not crash-loop the whole
    # server (which would leave health checks unanswerable). Log loudly and start
    # in a degraded state so operators can diagnose via logs and /health.
    try:
        app.state.rag_pipeline = RagPipeline.from_settings(settings)
        app.state.llm_provider = get_llm_provider(settings)
        logger.info(
            "Engines ready (llm=%s, vector_store=%s)",
            settings.llm_provider,
            settings.vector_store,
        )
    except Exception:
        logger.exception("Engine construction failed; starting in degraded mode")
        app.state.rag_pipeline = None
        app.state.llm_provider = None

    try:
        yield
    finally:
        await dispose_db()
        from app.cache.redis import close_redis

        await close_redis()
        logger.info("Shutdown complete")

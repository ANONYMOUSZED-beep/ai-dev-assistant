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
    import asyncio

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

    # Warm ML models in the background so the first user request doesn't hit the
    # platform request timeout (e.g. HF Spaces ~60s) while models download/load.
    warmup_task: asyncio.Task[None] | None = None
    if app.state.rag_pipeline is not None:

        async def _warmup() -> None:
            try:
                logger.info("Warming up ML models in background...")
                await app.state.rag_pipeline.warmup()
                logger.info("Model warmup complete")
            except Exception:
                logger.exception("Model warmup failed (models will load lazily)")

            # Seed the default "Getting Started" knowledge base so a first-time user
            # gets a real, cited answer instead of an empty collection. Idempotent.
            try:
                from app.rag.seed import (
                    GETTING_STARTED_COLLECTION,
                    getting_started_documents,
                )

                seeded = await app.state.rag_pipeline.seed_if_empty(
                    GETTING_STARTED_COLLECTION, getting_started_documents()
                )
                if seeded:
                    logger.info("Seeded Getting Started knowledge base (%d chunks)", seeded)
            except Exception:
                logger.exception("Getting Started seeding failed (non-fatal)")

        warmup_task = asyncio.create_task(_warmup())

    try:
        yield
    finally:
        if warmup_task is not None and not warmup_task.done():
            warmup_task.cancel()
        await dispose_db()
        from app.cache.redis import close_redis

        await close_redis()
        logger.info("Shutdown complete")

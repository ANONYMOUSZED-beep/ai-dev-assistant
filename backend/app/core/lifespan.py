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

    # Build engines defensively: a failure here must not crash-loop the whole
    # server (which would leave health checks unanswerable). Log loudly and start
    # in a degraded state so operators can diagnose via logs and /health.
    # NOTE: engine construction is cheap and touches no network (models load
    # lazily; the pgvector pool connects on first use), so it is safe to do here.
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

    # CRITICAL: everything that touches the network (DB init, model warmup, seeding)
    # runs in a background task so it can NEVER block uvicorn from binding the port.
    # A hanging asyncpg connection to a cold/unreachable managed DB here would
    # otherwise stall the ASGI lifespan "startup" event forever, leaving the Space
    # stuck in APP_STARTING with the health check unanswerable. Binding first means
    # /health and / respond immediately and the app self-heals as the DB warms up.
    async def _startup() -> None:
        # Idempotent schema create + additive migrations. Bounded so a stalled
        # connection can't wedge startup; it retries on the next deploy/boot.
        try:
            await asyncio.wait_for(init_db(), timeout=30)
        except Exception as exc:
            logger.warning("Database initialisation skipped/timed out: %s", exc)

        if app.state.rag_pipeline is None:
            return

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

    warmup_task: asyncio.Task[None] = asyncio.create_task(_startup())

    try:
        yield
    finally:
        if not warmup_task.done():
            warmup_task.cancel()
        await dispose_db()
        from app.cache.redis import close_redis

        await close_redis()
        logger.info("Shutdown complete")

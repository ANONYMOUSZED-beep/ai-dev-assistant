"""Error tracking via Sentry.

Initialised only when ``SENTRY_DSN`` is configured, so local development and tests
run untouched. The Sentry SDK auto-instruments FastAPI/Starlette and logging.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_initialized = False


def init_sentry(settings: Settings) -> None:
    """Initialise Sentry if a DSN is configured; otherwise do nothing."""
    global _initialized
    if _initialized or not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            # Keep well within the free tier: sample a small share of traces.
            traces_sample_rate=0.1,
            # Don't attach request bodies / user PII to events by default.
            send_default_pii=False,
        )
        _initialized = True
        logger.info("Sentry error tracking initialised (%s)", settings.environment)
    except Exception:  # noqa: BLE001 - never let observability setup break startup
        logger.exception("Sentry initialisation failed; continuing without it")

"""API authentication and rate limiting.

Two lightweight, dependency-based guards protect the data endpoints:

* :func:`require_api_key` — validates an ``X-API-Key`` header against the set of
  keys configured via ``API_KEYS``. When no keys are configured (typical for local
  development) authentication is disabled so the app stays friction-free.
* :func:`enforce_rate_limit` — a fixed-window limiter backed by Redis, keyed by API
  key (or client IP as a fallback). If Redis is unavailable the limiter *degrades
  open* rather than failing requests, so a cache outage never takes the API down.
"""

from __future__ import annotations

from fastapi import Request

from app.cache.redis import get_redis
from app.core.deps import SettingsDep
from app.core.exceptions import AuthError, RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)

_API_KEY_HEADER = "x-api-key"


def _client_identifier(request: Request) -> str:
    """Derive a stable identity for rate limiting from the request."""
    api_key = request.headers.get(_API_KEY_HEADER)
    if api_key:
        return f"key:{api_key}"
    client = request.client
    return f"ip:{client.host}" if client else "ip:anonymous"


async def require_api_key(request: Request, settings: SettingsDep) -> None:
    """Reject requests lacking a valid ``X-API-Key`` when keys are configured.

    No-op when ``settings.api_keys`` is empty, keeping local development open.
    """
    allowed = settings.api_keys
    if not allowed:
        return
    provided = request.headers.get(_API_KEY_HEADER)
    if provided is None or provided not in allowed:
        raise AuthError("Missing or invalid API key")


async def _hit_within_window(client, key: str, limit: int, window_seconds: int) -> bool:
    """Increment a fixed-window counter and report whether it stays within ``limit``.

    The first hit in a window sets the key's expiry, so counters reset automatically.
    """
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, window_seconds)
    return count <= limit


async def enforce_rate_limit(request: Request, settings: SettingsDep) -> None:
    """Apply a per-minute fixed-window rate limit; degrade open if Redis is down."""
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return

    identifier = _client_identifier(request)
    key = f"ratelimit:{identifier}"
    try:
        client = get_redis(settings)
        within = await _hit_within_window(client, key, limit, window_seconds=60)
    except Exception as exc:  # noqa: BLE001 - never fail a request on cache errors
        logger.warning("Rate limiter unavailable, allowing request: %s", exc)
        return

    if not within:
        raise RateLimitError(
            "Rate limit exceeded. Please slow down and try again shortly.",
            details={"limit_per_minute": limit},
        )


def auth_and_rate_limit_dependencies() -> list:
    """Dependency list applied to every protected router."""
    from fastapi import Depends

    return [Depends(require_api_key), Depends(enforce_rate_limit)]

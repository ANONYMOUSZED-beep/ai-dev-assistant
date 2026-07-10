"""Request rate limiting.

:func:`enforce_rate_limit` is a fixed-window limiter backed by Redis, keyed by the
bearer token (or client IP as a fallback). If Redis is unavailable the limiter
*degrades open* rather than failing requests, so a cache outage never takes the
API down. Authentication itself is handled by ``app.core.deps.get_current_user``.
"""

from __future__ import annotations

from fastapi import Request

from app.cache.redis import get_redis
from app.core.deps import SettingsDep
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _client_identifier(request: Request) -> str:
    """Derive a stable identity for rate limiting from the request."""
    auth = request.headers.get("authorization", "")
    if auth:
        return f"tok:{auth[-24:]}"  # tail of the bearer token, avoids logging full token
    client = request.client
    return f"ip:{client.host}" if client else "ip:anonymous"


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

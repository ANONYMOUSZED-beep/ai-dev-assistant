"""Async Redis client with small JSON helpers for caching and job status."""

from __future__ import annotations

from typing import Any

import orjson
import redis.asyncio as aioredis

from app.core.config import Settings, get_settings

_client: aioredis.Redis | None = None


def get_redis(settings: Settings | None = None) -> aioredis.Redis:
    """Return the process-wide async Redis client."""
    global _client
    if _client is None:
        settings = settings or get_settings()
        _client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _client


async def close_redis() -> None:
    """Close the Redis client on shutdown."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


class RedisCache:
    """Thin JSON-serialising wrapper around the async Redis client."""

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    async def get_json(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        return orjson.loads(raw) if raw else None

    async def set_json(self, key: str, value: Any, ttl: int | None = None) -> None:
        data = orjson.dumps(value).decode()
        await self._client.set(key, data, ex=ttl)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

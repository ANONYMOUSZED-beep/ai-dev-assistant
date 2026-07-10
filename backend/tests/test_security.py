"""Tests for JWT auth enforcement and the rate limiter."""

from __future__ import annotations

import pytest
from app.core.security import _hit_within_window
from app.main import app
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio


class _FakeRedis:
    """Minimal async Redis stand-in supporting incr/expire for limiter tests."""

    def __init__(self) -> None:
        self.store: dict[str, int] = {}
        self.expiries: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expiries[key] = seconds


async def test_protected_endpoint_requires_token() -> None:
    """Without an Authorization header, a protected endpoint returns 401.

    Uses a raw client (no auth override) — this asserts the real guard.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/chat", json={"question": "hi"})
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "unauthorized"


async def test_health_is_public() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")
        assert resp.status_code == 200


async def test_rate_limiter_counts_and_blocks() -> None:
    fake = _FakeRedis()
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is True
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is True
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is False
    assert fake.expiries["k"] == 60


async def test_rate_limiter_sets_expiry_once() -> None:
    fake = _FakeRedis()
    await _hit_within_window(fake, "k", limit=10, window_seconds=60)
    await _hit_within_window(fake, "k", limit=10, window_seconds=60)
    assert fake.store["k"] == 2
    assert fake.expiries == {"k": 60}

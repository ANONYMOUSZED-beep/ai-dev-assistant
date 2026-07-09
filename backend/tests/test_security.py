"""Tests for API-key authentication and the rate limiter."""

from __future__ import annotations

import pytest
from app.core.config import Settings, get_settings
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


async def test_public_health_needs_no_key(client: AsyncClient) -> None:
    # Auth is disabled by default (no API_KEYS configured) so this always passes,
    # but health is public regardless.
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200


async def test_protected_endpoint_open_when_no_keys(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"question": "hi"})
    assert resp.status_code == 200


async def test_auth_rejects_without_key_when_configured() -> None:
    """With API_KEYS set, protected endpoints require a matching X-API-Key header."""
    app.dependency_overrides[get_settings] = lambda: Settings(
        api_keys=["secret-key"], rate_limit_per_minute=0
    )
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            missing = await ac.post("/api/v1/chat", json={"question": "hi"})
            assert missing.status_code == 401
            assert missing.json()["error"]["code"] == "unauthorized"

            wrong = await ac.post(
                "/api/v1/chat",
                json={"question": "hi"},
                headers={"X-API-Key": "nope"},
            )
            assert wrong.status_code == 401

            ok = await ac.post(
                "/api/v1/chat",
                json={"question": "hi"},
                headers={"X-API-Key": "secret-key"},
            )
            assert ok.status_code == 200

            # Health stays public even with auth enabled.
            health = await ac.get("/api/v1/health")
            assert health.status_code == 200
    finally:
        app.dependency_overrides.pop(get_settings, None)


async def test_rate_limiter_counts_and_blocks() -> None:
    fake = _FakeRedis()
    # Limit of 2 within the window: first two allowed, third blocked.
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is True
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is True
    assert await _hit_within_window(fake, "k", limit=2, window_seconds=60) is False
    # Expiry is set exactly once, on the first hit of the window.
    assert fake.expiries["k"] == 60


async def test_rate_limiter_sets_expiry_once() -> None:
    fake = _FakeRedis()
    await _hit_within_window(fake, "k", limit=10, window_seconds=60)
    await _hit_within_window(fake, "k", limit=10, window_seconds=60)
    # incr called twice, but expire only on the first.
    assert fake.store["k"] == 2
    assert fake.expiries == {"k": 60}

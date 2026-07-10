"""Tests for request-context middleware and the readiness probe."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_request_id_and_timing_headers(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
    assert resp.headers.get("X-Response-Time-ms")


async def test_inbound_request_id_is_preserved(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/health", headers={"X-Request-ID": "trace-abc-123"}
    )
    assert resp.headers.get("X-Request-ID") == "trace-abc-123"


async def test_readiness_reports_dependency_checks(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health/ready")
    # No Redis/DB in the test environment → not ready (503); shape is always present.
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert body["status"] in ("ready", "not_ready")
    assert set(body["checks"]) == {"redis", "database"}

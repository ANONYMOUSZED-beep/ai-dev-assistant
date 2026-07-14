"""Tests for shareable read-only conversation links."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_share_then_public_view_without_auth(client: AsyncClient) -> None:
    """An owner can publish a conversation; anyone can view it via the share link."""
    resp = await client.post("/api/v1/chat", json={"question": "What is a monad?"})
    assert resp.status_code == 200
    cid = resp.json()["conversation_id"]

    shared = await client.post(f"/api/v1/conversations/{cid}/share")
    assert shared.status_code == 200
    body = shared.json()
    share_id = body["share_id"]
    assert share_id
    assert body["url_path"] == f"/share/{share_id}"

    # Public endpoint carries no auth dependency at all.
    public = await client.get(f"/api/v1/share/{share_id}", headers={})
    assert public.status_code == 200
    detail = public.json()
    assert detail["id"] == cid
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]


async def test_share_is_idempotent(client: AsyncClient) -> None:
    """Publishing twice returns the same share token."""
    cid = (
        await client.post("/api/v1/chat", json={"question": "Idempotent?"})
    ).json()["conversation_id"]

    first = await client.post(f"/api/v1/conversations/{cid}/share")
    second = await client.post(f"/api/v1/conversations/{cid}/share")
    assert first.json()["share_id"] == second.json()["share_id"]


async def test_unshare_revokes_public_access(client: AsyncClient) -> None:
    """After unsharing, the public link 404s."""
    cid = (
        await client.post("/api/v1/chat", json={"question": "Revoke me?"})
    ).json()["conversation_id"]
    share_id = (
        await client.post(f"/api/v1/conversations/{cid}/share")
    ).json()["share_id"]

    unshared = await client.delete(f"/api/v1/conversations/{cid}/share")
    assert unshared.status_code == 200
    assert unshared.json() == {"unshared": cid}

    assert (await client.get(f"/api/v1/share/{share_id}")).status_code == 404


async def test_unknown_share_id_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/share/does-not-exist")).status_code == 404

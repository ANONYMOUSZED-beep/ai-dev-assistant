"""Tests for chat history persistence and the conversations API."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_docs_chat_persists_conversation(client: AsyncClient) -> None:
    """A docs chat turn should create a 'docs' conversation with two messages."""
    resp = await client.post(
        "/api/v1/chat", json={"question": "What is dependency injection?"}
    )
    assert resp.status_code == 200
    conversation_id = resp.json()["conversation_id"]
    assert conversation_id

    listing = await client.get("/api/v1/conversations")
    assert listing.status_code == 200
    convos = listing.json()
    assert len(convos) == 1
    assert convos[0]["kind"] == "docs"
    assert convos[0]["message_count"] == 2
    assert convos[0]["title"]

    detail = await client.get(f"/api/v1/conversations/{conversation_id}")
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]


async def test_followup_reuses_same_conversation(client: AsyncClient) -> None:
    """Passing conversation_id should append to the existing conversation."""
    first = await client.post("/api/v1/chat", json={"question": "First question?"})
    cid = first.json()["conversation_id"]

    second = await client.post(
        "/api/v1/chat",
        json={"question": "Follow up?", "conversation_id": cid},
    )
    assert second.json()["conversation_id"] == cid

    detail = await client.get(f"/api/v1/conversations/{cid}")
    assert len(detail.json()["messages"]) == 4


async def test_kind_filter_and_delete(client: AsyncClient) -> None:
    """Conversations can be filtered by kind and deleted."""
    await client.post("/api/v1/chat", json={"question": "Docs question?"})
    await client.post("/api/v1/pair", json={"action": "explain", "code": "x = 1"})

    docs_only = await client.get("/api/v1/conversations", params={"kind": "docs"})
    assert all(c["kind"] == "docs" for c in docs_only.json())
    pair_only = await client.get("/api/v1/conversations", params={"kind": "pair"})
    assert len(pair_only.json()) == 1
    assert pair_only.json()[0]["kind"] == "pair"

    cid = pair_only.json()[0]["id"]
    deleted = await client.delete(f"/api/v1/conversations/{cid}")
    assert deleted.status_code == 200
    assert (await client.get(f"/api/v1/conversations/{cid}")).status_code == 404


async def test_rename_conversation(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"question": "Rename me?"})
    cid = resp.json()["conversation_id"]

    renamed = await client.patch(
        f"/api/v1/conversations/{cid}", json={"title": "Custom title"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Custom title"


async def test_missing_conversation_returns_404(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/conversations/nope")).status_code == 404

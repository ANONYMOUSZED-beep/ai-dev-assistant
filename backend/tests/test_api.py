"""Integration tests for the API endpoints (engines faked via app.state)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "llm_provider" in body


async def test_doc_chat_returns_answer_with_citations(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/chat", json={"question": "How does FastAPI work?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"].startswith("ANSWER[")
    assert body["provider"] == "fake"
    assert len(body["citations"]) == 1
    assert body["citations"][0]["title"] == "FastAPI Docs"
    assert body["citations"][0]["index"] == 1


async def test_doc_chat_stream(client: AsyncClient) -> None:
    payload = {"question": "stream please"}
    async with client.stream("POST", "/api/v1/chat/stream", json=payload) as resp:
        assert resp.status_code == 200
        text = ""
        async for line in resp.aiter_lines():
            text += line
    assert "citations" in text
    assert "Hello" in text and "world" in text


async def test_ingest_text(client: AsyncClient) -> None:
    payload = {"collection": "docs", "text": "Some documentation content.", "title": "T"}
    resp = await client.post("/api/v1/documents/ingest", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["collection"] == "docs"
    assert body["chunks_indexed"] >= 1


async def test_ingest_requires_source(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/documents/ingest", json={"collection": "docs"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ingestion_error"


async def test_code_search(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/search/code", json={"query": "where is auth", "top_k": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "where is auth"
    assert len(body["hits"]) == 1
    assert body["hits"][0]["path"]


async def test_debug(client: AsyncClient) -> None:
    payload = {"error": "Traceback ... ZeroDivisionError", "language": "python"}
    resp = await client.post("/api/v1/debug", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"].startswith("ANSWER[")
    assert len(body["citations"]) == 1


async def test_pair_explain(client: AsyncClient) -> None:
    payload = {"action": "explain", "code": "def f(): return 1", "language": "python"}
    resp = await client.post("/api/v1/pair", json=payload)
    assert resp.status_code == 200
    assert resp.json()["text"].startswith("ANSWER[")


async def test_pair_security_pulls_context(client: AsyncClient) -> None:
    payload = {"action": "security", "code": "eval(input())", "language": "python"}
    resp = await client.post("/api/v1/pair", json=payload)
    assert resp.status_code == 200
    # security action retrieves best-practice context -> citations present
    assert len(resp.json()["citations"]) == 1


async def test_invalid_pair_action(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/pair", json={"action": "nope", "code": "x"})
    assert resp.status_code == 422

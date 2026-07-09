"""Pytest fixtures.

Tests run against the FastAPI app with the heavy engines (RAG pipeline, LLM provider)
replaced by lightweight fakes attached to ``app.state``. We use httpx's ASGITransport,
which does not trigger the lifespan, so no models are loaded and no database/Redis is
required.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from app.main import app
from app.schemas.llm import LLMMessage, LLMResponse
from app.schemas.rag import Chunk, Document, RetrievedChunk, SourceType
from httpx import ASGITransport, AsyncClient


class FakeLLMProvider:
    """Deterministic LLM stand-in."""

    name = "fake"
    model = "fake-model"

    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        last = messages[-1].content if messages else ""
        return LLMResponse(
            content=f"ANSWER[{last[:40]}]",
            model=self.model,
            provider=self.name,
            prompt_tokens=10,
            completion_tokens=5,
        )

    async def stream(self, messages: list[LLMMessage]) -> AsyncIterator[str]:
        for token in ["Hello", " ", "world"]:
            yield token


class FakeRagPipeline:
    """In-memory RAG stand-in returning a fixed retrieved chunk."""

    def __init__(self) -> None:
        self.ingested: list[tuple[str, int]] = []

    async def ingest(self, documents: list[Document], collection: str) -> int:
        count = sum(max(1, len(d.content) // 50) for d in documents)
        self.ingested.append((collection, count))
        return count

    async def retrieve(
        self, query: str, collection: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        chunk = Chunk(
            id="c1",
            document_id="d1",
            content="FastAPI uses Starlette and Pydantic for async APIs.",
            source_type=SourceType.MARKDOWN,
            source_id="fastapi/index.md",
            title="FastAPI Docs",
            uri="https://fastapi.tiangolo.com/",
            start_line=1,
            end_line=3,
        )
        return [RetrievedChunk(chunk=chunk, score=0.9, rerank_score=0.95)]

    def delete_collection(self, collection: str) -> None:
        return None


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.state.rag_pipeline = FakeRagPipeline()
    app.state.llm_provider = FakeLLMProvider()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

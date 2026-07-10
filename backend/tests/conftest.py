"""Pytest fixtures.

Two client fixtures:

* ``client`` — engines faked and auth bypassed (``get_current_user`` overridden).
  Used to test the feature endpoints without a real database or token.
* ``db_client`` — a real in-memory SQLite database with auth *enabled*, for
  testing registration/login and anything that persists.

Both use httpx's ASGITransport, which does not trigger the lifespan.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import app.db.models  # noqa: F401 - register models on Base.metadata
import pytest_asyncio
from app.core.deps import get_current_user
from app.db.base import Base
from app.db.models import User
from app.db.session import get_session
from app.main import app
from app.schemas.llm import LLMMessage, LLMResponse
from app.schemas.rag import Chunk, Document, RetrievedChunk, SourceType
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool


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


def _fake_user() -> User:
    return User(id="test-user", username="tester", password_hash="")


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Authenticated (bypassed) client with faked engines."""
    app.state.rag_pipeline = FakeRagPipeline()
    app.state.llm_provider = FakeLLMProvider()
    app.dependency_overrides[get_current_user] = _fake_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def db_client() -> AsyncIterator[AsyncClient]:
    """Client backed by a real in-memory SQLite DB with auth enabled."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_session() -> AsyncIterator:
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.state.rag_pipeline = FakeRagPipeline()
    app.state.llm_provider = FakeLLMProvider()
    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_session, None)
    await engine.dispose()

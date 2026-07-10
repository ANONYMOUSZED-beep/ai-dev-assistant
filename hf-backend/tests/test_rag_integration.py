"""End-to-end integration tests for the *real* RAG pipeline.

Unlike ``test_api.py`` (which fakes the engines), these tests exercise the actual
chunking, FAISS vector store, hybrid dense+BM25 retrieval, and citation building.
Only the embedder and reranker are substituted with deterministic, download-free
stand-ins so the tests run fast and offline while still driving the real data path.
"""

from __future__ import annotations

import hashlib
import math
import re

import pytest
from app.main import app
from app.rag.chunking import Chunker
from app.rag.contracts import build_citations
from app.rag.pipeline import RagPipeline
from app.rag.vectorstore.faiss_store import FaissVectorStore
from app.schemas.llm import LLMMessage, LLMResponse
from app.schemas.rag import Document, RetrievedChunk, SourceType
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.asyncio

_TOKEN = re.compile(r"[a-z0-9]+")


class DeterministicEmbedder:
    """Hashing bag-of-words embedder producing L2-normalised vectors.

    Deterministic across runs (uses md5, not Python's salted hash), so documents
    sharing tokens with the query get a higher cosine similarity — enough to make
    retrieval assertions meaningful without loading a real model.
    """

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        for token in _TOKEN.findall(text.lower()):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim
            vec[bucket] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


class PassthroughReranker:
    """Reranker that preserves fused order and records a rerank score."""

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        return [rc.model_copy(update={"rerank_score": rc.score}) for rc in candidates][:top_k]


class FakeLLM:
    name = "fake"
    model = "fake-model"

    async def generate(self, messages: list[LLMMessage]) -> LLMResponse:
        return LLMResponse(
            content="Grounded answer [1].",
            model=self.model,
            provider=self.name,
            prompt_tokens=1,
            completion_tokens=1,
        )

    async def stream(self, messages):  # pragma: no cover - not used here
        yield "Grounded answer [1]."


def _build_pipeline(tmp_path) -> RagPipeline:
    return RagPipeline(
        embedder=DeterministicEmbedder(),
        vector_store=FaissVectorStore(str(tmp_path)),
        reranker=PassthroughReranker(),
        chunker=Chunker(chunk_size=400, chunk_overlap=60),
        retrieval_top_k=10,
        rerank_top_k=5,
    )


def _docs() -> list[Document]:
    return [
        Document(
            content=(
                "FastAPI dependency injection resolves shared resources per request "
                "using the Depends function and provider callables."
            ),
            source_type=SourceType.MARKDOWN,
            source_id="fastapi/di.md",
            title="FastAPI Dependency Injection",
            uri="https://fastapi.tiangolo.com/tutorial/dependencies/",
        ),
        Document(
            content=(
                "React hooks let function components manage state and side effects "
                "with useState and useEffect."
            ),
            source_type=SourceType.MARKDOWN,
            source_id="react/hooks.md",
            title="React Hooks",
        ),
        Document(
            content=(
                "Docker packages applications into portable containers built from a "
                "Dockerfile and distributed as images."
            ),
            source_type=SourceType.MARKDOWN,
            source_id="docker/intro.md",
            title="Docker Basics",
        ),
    ]


async def test_pipeline_ingest_and_retrieve_ranks_relevant_doc(tmp_path) -> None:
    pipe = _build_pipeline(tmp_path)

    indexed = await pipe.ingest(_docs(), "docs")
    assert indexed >= 3  # each short doc yields at least one chunk

    results = await pipe.retrieve("FastAPI dependency injection with Depends", "docs")
    assert results, "expected at least one retrieved chunk"
    # The most relevant document must rank first.
    assert results[0].chunk.source_id == "fastapi/di.md"
    # Hybrid scoring populated the transparency fields.
    assert results[0].rerank_score is not None


async def test_pipeline_retrieves_by_topic(tmp_path) -> None:
    pipe = _build_pipeline(tmp_path)
    await pipe.ingest(_docs(), "docs")

    react = await pipe.retrieve("react useState hooks state", "docs")
    assert react[0].chunk.source_id == "react/hooks.md"

    docker = await pipe.retrieve("docker container image Dockerfile", "docs")
    assert docker[0].chunk.source_id == "docker/intro.md"


async def test_citations_built_from_real_retrieval(tmp_path) -> None:
    pipe = _build_pipeline(tmp_path)
    await pipe.ingest(_docs(), "docs")
    results = await pipe.retrieve("FastAPI Depends dependency injection", "docs")

    citations = build_citations(results)
    assert citations
    assert [c.index for c in citations] == list(range(1, len(citations) + 1))
    assert citations[0].title == "FastAPI Dependency Injection"
    assert citations[0].uri == "https://fastapi.tiangolo.com/tutorial/dependencies/"


async def test_delete_collection_clears_index(tmp_path) -> None:
    pipe = _build_pipeline(tmp_path)
    await pipe.ingest(_docs(), "docs")
    pipe.delete_collection("docs")
    assert await pipe.retrieve("anything", "docs") == []


async def test_full_request_path_with_real_pipeline(tmp_path) -> None:
    """Drive the API with the real pipeline + a fake LLM: ingest, then chat, and
    assert the answer's citations came from genuine retrieval."""
    from app.core.deps import get_current_user
    from app.db.models import User

    app.state.rag_pipeline = _build_pipeline(tmp_path)
    app.state.llm_provider = FakeLLM()
    app.dependency_overrides[get_current_user] = lambda: User(
        id="test-user", username="tester", password_hash=""
    )

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for doc in _docs():
                resp = await client.post(
                    "/api/v1/documents/ingest",
                    json={
                        "collection": "docs",
                        "text": doc.content,
                        "title": doc.title,
                    },
                )
                assert resp.status_code == 200

            answer = await client.post(
                "/api/v1/chat",
                json={"question": "How does FastAPI dependency injection work?"},
            )
            assert answer.status_code == 200
            body = answer.json()
            assert body["provider"] == "fake"
            assert len(body["citations"]) >= 1
            # The top citation should be the FastAPI doc, proving real retrieval ran.
            assert any("FastAPI" in c["title"] for c in body["citations"])
    finally:
        app.dependency_overrides.pop(get_current_user, None)

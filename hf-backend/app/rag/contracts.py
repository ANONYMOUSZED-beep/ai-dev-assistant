"""Authoritative RAG contracts.

Defines the structural interfaces (Protocols) for the swappable RAG components and the
public surface of :class:`~app.rag.pipeline.RagPipeline`. Concrete implementations must
satisfy these protocols; the services layer depends only on what is declared here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas.rag import Chunk, Citation, Document, RetrievedChunk


@runtime_checkable
class Embedder(Protocol):
    """Turns text into dense vectors (e.g. BGE-M3 via sentence-transformers)."""

    @property
    def dimension(self) -> int:
        """Embedding dimensionality."""
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        ...


@runtime_checkable
class VectorStore(Protocol):
    """Persistent dense index, isolated per ``collection``."""

    def add(self, collection: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Index ``chunks`` with their precomputed ``vectors`` in ``collection``."""
        ...

    def search(
        self, collection: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        """Return the ``top_k`` nearest chunks in ``collection``."""
        ...

    def all_chunks(self, collection: str) -> list[Chunk]:
        """Return every chunk in ``collection`` (used to build the sparse index)."""
        ...

    def delete_collection(self, collection: str) -> None:
        """Remove an entire collection."""
        ...


@runtime_checkable
class Reranker(Protocol):
    """Cross-encoder reranker applied to retrieved candidates."""

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Reorder ``candidates`` by relevance to ``query`` and keep the best ``top_k``."""
        ...


@runtime_checkable
class DocumentLoader(Protocol):
    """Loads a raw source into normalised :class:`Document` objects."""

    def load(self, source: str, **options: object) -> list[Document]:
        """Load ``source`` (path, url, or identifier) into documents."""
        ...


def build_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Convert retrieved chunks into ordered, human-readable citations.

    Implemented here (rather than in the pipeline) so it can be reused and unit-tested
    independently of the heavier retrieval components.
    """
    citations: list[Citation] = []
    for i, rc in enumerate(chunks, start=1):
        chunk = rc.chunk
        snippet = chunk.content.strip().replace("\n", " ")
        if len(snippet) > 240:
            snippet = snippet[:237] + "..."
        citations.append(
            Citation(
                index=i,
                title=chunk.title or chunk.source_id,
                source_type=chunk.source_type,
                uri=chunk.uri,
                snippet=snippet,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                score=rc.rerank_score if rc.rerank_score is not None else rc.score,
            )
        )
    return citations

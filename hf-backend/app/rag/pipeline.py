"""The RAG pipeline: ingestion → chunking → embedding → hybrid retrieval → reranking.

Construction is cheap and side-effect free: embedder, vector store, reranker, retriever
and chunker are wired together without loading any ML models. Models load lazily on first
use. Synchronous ML/IO work is dispatched to threads via :func:`asyncio.to_thread` so the
async API surface never blocks the event loop.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.rag.chunking import Chunker
from app.rag.embeddings import BGEEmbedder
from app.rag.retrieval import CrossEncoderReranker, HybridRetriever
from app.rag.vectorstore import get_vector_store
from app.schemas.rag import Chunk, Document, RetrievedChunk

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.rag.contracts import Embedder, Reranker, VectorStore


class RagPipeline:
    """Orchestrates the end-to-end retrieval-augmented-generation data path."""

    def __init__(
        self,
        *,
        embedder: Embedder,
        vector_store: VectorStore,
        reranker: Reranker,
        chunker: Chunker,
        retrieval_top_k: int,
        rerank_top_k: int,
    ) -> None:
        self._embedder = embedder
        self._store = vector_store
        self._reranker = reranker
        self._chunker = chunker
        self._retriever = HybridRetriever(vector_store)
        self._retrieval_top_k = retrieval_top_k
        self._rerank_top_k = rerank_top_k

    @classmethod
    def from_settings(cls, settings: Settings) -> RagPipeline:
        """Build a pipeline from application settings without loading any models."""
        return cls(
            embedder=BGEEmbedder(settings.embedding_model),
            vector_store=get_vector_store(settings),
            reranker=CrossEncoderReranker(settings.reranker_model),
            chunker=Chunker(settings.chunk_size, settings.chunk_overlap),
            retrieval_top_k=settings.retrieval_top_k,
            rerank_top_k=settings.rerank_top_k,
        )

    async def ingest(self, documents: list[Document], collection: str) -> int:
        """Chunk, embed and index ``documents`` into ``collection``.

        Returns the total number of chunks indexed.
        """
        if not documents:
            return 0
        chunks = await asyncio.to_thread(self._chunker.chunk_documents, documents)
        if not chunks:
            return 0
        texts = [chunk.content for chunk in chunks]
        vectors = await asyncio.to_thread(self._embedder.embed_documents, texts)
        await asyncio.to_thread(self._store.add, collection, chunks, vectors)
        return len(chunks)

    async def retrieve(
        self, query: str, collection: str, top_k: int | None = None
    ) -> list[RetrievedChunk]:
        """Retrieve and rerank the most relevant chunks for ``query``."""
        candidate_k = top_k or self._retrieval_top_k
        query_vector = await asyncio.to_thread(self._embedder.embed_query, query)
        candidates = await asyncio.to_thread(
            self._retriever.retrieve, collection, query, query_vector, candidate_k
        )
        if not candidates:
            return []
        final_k = top_k or self._rerank_top_k
        return await asyncio.to_thread(
            self._reranker.rerank, query, candidates, final_k
        )

    async def warmup(self) -> None:
        """Eagerly load ML models so the first user request doesn't pay the cold-start cost.

        On platforms with a request-level proxy timeout (e.g. Hugging Face Spaces ~60s),
        loading the embedding/reranker models lazily on the first ``/documents/ingest``
        call can exceed the timeout and drop the connection. Warming them at startup in
        the background moves that cost off the request path.
        """
        for component in (self._embedder, self._reranker):
            warmup = getattr(component, "warmup", None)
            if callable(warmup):
                await asyncio.to_thread(warmup)

    def delete_collection(self, collection: str) -> None:
        """Remove an entire collection from the vector store."""
        self._store.delete_collection(collection)

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Expose synchronous chunking (useful for tooling/tests)."""
        return self._chunker.chunk_documents(documents)

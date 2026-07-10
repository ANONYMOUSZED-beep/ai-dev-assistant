"""Vector store factory.

Selects the concrete :class:`app.rag.contracts.VectorStore` implementation based on
``settings.vector_store``. Construction is cheap; heavy backend imports happen lazily
inside the store implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.rag.contracts import VectorStore


def get_vector_store(settings: Settings) -> VectorStore:
    """Return the configured vector store instance."""
    name = settings.vector_store
    if name == "faiss":
        from app.rag.vectorstore.faiss_store import FaissVectorStore

        return FaissVectorStore(settings.vector_store_path)
    if name == "chroma":
        from app.rag.vectorstore.chroma_store import ChromaVectorStore

        return ChromaVectorStore(settings.vector_store_path)
    if name == "pgvector":
        from app.db.session import get_sync_dsn
        from app.rag.vectorstore.pgvector_store import PgVectorStore

        return PgVectorStore(get_sync_dsn(settings))
    raise ValueError(f"Unsupported vector store: {name!r}")

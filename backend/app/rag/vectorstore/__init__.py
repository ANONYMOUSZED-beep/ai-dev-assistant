"""Pluggable persistent vector stores (FAISS, Chroma)."""

from app.rag.vectorstore.factory import get_vector_store

__all__ = ["get_vector_store"]

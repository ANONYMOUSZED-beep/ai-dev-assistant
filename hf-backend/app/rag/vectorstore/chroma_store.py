"""Chroma-backed vector store using a local persistent client.

Each logical collection maps to one Chroma collection configured for cosine space.
The full :class:`Chunk` payload is serialised into the per-record metadata so chunks can
be faithfully reconstructed for both dense search and sparse (BM25) index building.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from typing import TYPE_CHECKING

from app.schemas.rag import Chunk, RetrievedChunk

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_CHUNK_KEY = "chunk_json"


class ChromaVectorStore:
    """VectorStore implementation backed by ``chromadb.PersistentClient``."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._client: ClientAPI | None = None

    def add(self, collection: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        coll = self._collection(collection)
        coll.add(
            ids=[chunk.id for chunk in chunks],
            embeddings=[list(map(float, vector)) for vector in vectors],
            documents=[chunk.content for chunk in chunks],
            metadatas=[{_CHUNK_KEY: chunk.model_dump_json()} for chunk in chunks],
        )

    def search(
        self, collection: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        coll = self._collection(collection)
        count = coll.count()
        if count == 0:
            return []
        result = coll.query(
            query_embeddings=[list(map(float, query_vector))],
            n_results=min(top_k, count),
            include=["metadatas", "distances"],
        )
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        results: list[RetrievedChunk] = []
        for metadata, distance in zip(metadatas, distances, strict=False):
            chunk = self._decode(metadata)
            if chunk is None:
                continue
            score = 1.0 - float(distance)
            results.append(
                RetrievedChunk(chunk=chunk, score=score, dense_score=score)
            )
        return results

    def all_chunks(self, collection: str) -> list[Chunk]:
        coll = self._collection(collection)
        if coll.count() == 0:
            return []
        result = coll.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []
        chunks: list[Chunk] = []
        for metadata in metadatas:
            chunk = self._decode(metadata)
            if chunk is not None:
                chunks.append(chunk)
        return chunks

    def delete_collection(self, collection: str) -> None:
        client = self._ensure_client()
        try:
            client.delete_collection(self._slug(collection))
        except (ValueError, KeyError):
            # Collection does not exist; deletion is a no-op.
            return

    # ── Internals ────────────────────────────────────────────────
    def _ensure_client(self) -> ClientAPI:
        if self._client is None:
            with self._lock:
                if self._client is None:
                    import chromadb

                    self._client = chromadb.PersistentClient(path=self._path)
        return self._client

    def _collection(self, collection: str):  # noqa: ANN202 - chromadb Collection type
        client = self._ensure_client()
        return client.get_or_create_collection(
            name=self._slug(collection),
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _decode(metadata: dict[str, object] | None) -> Chunk | None:
        if not metadata:
            return None
        raw = metadata.get(_CHUNK_KEY)
        if not isinstance(raw, str):
            return None
        return Chunk.model_validate(json.loads(raw))

    @staticmethod
    def _slug(collection: str) -> str:
        safe = _SAFE_NAME.sub("_", collection).strip("_") or "default"
        digest = hashlib.sha256(collection.encode("utf-8")).hexdigest()[:8]
        return f"{safe[:48]}_{digest}"[:63]

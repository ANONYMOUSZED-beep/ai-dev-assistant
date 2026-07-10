"""FAISS-backed vector store.

One ``IndexFlatIP`` is maintained per collection and persisted under
``settings.vector_store_path`` alongside a JSON sidecar holding the chunk metadata
(FAISS stores only vectors, not payloads). Vectors are expected to be L2-normalised, so
inner-product search yields cosine similarity.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from typing import TYPE_CHECKING

from app.schemas.rag import Chunk, RetrievedChunk

if TYPE_CHECKING:
    import faiss

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class FaissVectorStore:
    """VectorStore implementation persisting one flat IP index per collection."""

    def __init__(self, path: str) -> None:
        self._base_path = path
        self._lock = threading.Lock()
        os.makedirs(self._base_path, exist_ok=True)

    def add(self, collection: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        import numpy as np

        matrix = np.asarray(vectors, dtype="float32")
        dim = matrix.shape[1]
        with self._lock:
            index = self._load_index(collection, dim)
            metadata = self._load_metadata(collection)
            index.add(matrix)
            metadata.extend(chunk.model_dump() for chunk in chunks)
            self._persist(collection, index, metadata)

    def search(
        self, collection: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        import numpy as np

        with self._lock:
            metadata = self._load_metadata(collection)
            if not metadata:
                return []
            index = self._load_index(collection, len(query_vector))
            if index.ntotal == 0:
                return []
            query = np.asarray([query_vector], dtype="float32")
            k = min(top_k, index.ntotal)
            scores, indices = index.search(query, k)

        results: list[RetrievedChunk] = []
        for score, idx in zip(scores[0].tolist(), indices[0].tolist(), strict=False):
            if idx < 0 or idx >= len(metadata):
                continue
            chunk = Chunk.model_validate(metadata[idx])
            results.append(
                RetrievedChunk(chunk=chunk, score=float(score), dense_score=float(score))
            )
        return results

    def all_chunks(self, collection: str) -> list[Chunk]:
        with self._lock:
            metadata = self._load_metadata(collection)
        return [Chunk.model_validate(item) for item in metadata]

    def delete_collection(self, collection: str) -> None:
        with self._lock:
            for path in (self._index_path(collection), self._meta_path(collection)):
                if os.path.exists(path):
                    os.remove(path)

    # ── Internals ────────────────────────────────────────────────
    def _load_index(self, collection: str, dim: int) -> faiss.Index:
        import faiss

        path = self._index_path(collection)
        if os.path.exists(path):
            return faiss.read_index(path)
        return faiss.IndexFlatIP(dim)

    def _load_metadata(self, collection: str) -> list[dict[str, object]]:
        path = self._meta_path(collection)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _persist(
        self, collection: str, index: faiss.Index, metadata: list[dict[str, object]]
    ) -> None:
        import faiss

        faiss.write_index(index, self._index_path(collection))
        with open(self._meta_path(collection), "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, ensure_ascii=False)

    def _index_path(self, collection: str) -> str:
        return os.path.join(self._base_path, f"{self._slug(collection)}.faiss")

    def _meta_path(self, collection: str) -> str:
        return os.path.join(self._base_path, f"{self._slug(collection)}.json")

    @staticmethod
    def _slug(collection: str) -> str:
        safe = _SAFE_NAME.sub("_", collection).strip("_") or "default"
        digest = hashlib.sha256(collection.encode("utf-8")).hexdigest()[:8]
        return f"{safe[:48]}_{digest}"

"""Hybrid retrieval fusing dense vector search with sparse BM25 ranking.

Dense candidates come from the vector store; sparse candidates are scored with
``rank_bm25.BM25Okapi`` over every chunk in the collection. The two score sets are
min-max normalised to ``[0, 1]`` and combined with configurable weights.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.schemas.rag import RetrievedChunk

if TYPE_CHECKING:
    from app.rag.contracts import VectorStore

_TOKEN_RE = re.compile(r"\w+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _normalize(scores: dict[str, float]) -> dict[str, float]:
    """Min-max normalise a mapping of id -> raw score into ``[0, 1]``."""
    if not scores:
        return {}
    values = list(scores.values())
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return {key: 1.0 for key in scores}
    span = hi - lo
    return {key: (value - lo) / span for key, value in scores.items()}


class HybridRetriever:
    """Combine dense and sparse retrieval over a single collection."""

    def __init__(
        self,
        store: VectorStore,
        *,
        dense_weight: float = 0.5,
        sparse_weight: float = 0.5,
    ) -> None:
        self._store = store
        self._dense_weight = dense_weight
        self._sparse_weight = sparse_weight

    def retrieve(
        self, collection: str, query: str, query_vector: list[float], top_k: int
    ) -> list[RetrievedChunk]:
        """Return up to ``top_k`` fused candidates for ``query``."""
        dense_results = self._store.search(collection, query_vector, top_k)
        all_chunks = self._store.all_chunks(collection)
        if not all_chunks:
            return dense_results

        sparse_by_id = self._bm25_scores(query, all_chunks, top_k)
        dense_raw = {rc.chunk.id: rc.score for rc in dense_results}
        dense_norm = _normalize(dense_raw)
        sparse_norm = _normalize(sparse_by_id)

        chunk_index = {chunk.id: chunk for chunk in all_chunks}
        for rc in dense_results:
            chunk_index[rc.chunk.id] = rc.chunk

        fused: list[RetrievedChunk] = []
        for chunk_id in set(dense_norm) | set(sparse_norm):
            chunk = chunk_index.get(chunk_id)
            if chunk is None:
                continue
            dense_component = dense_norm.get(chunk_id, 0.0)
            sparse_component = sparse_norm.get(chunk_id, 0.0)
            score = (
                self._dense_weight * dense_component
                + self._sparse_weight * sparse_component
            )
            fused.append(
                RetrievedChunk(
                    chunk=chunk,
                    score=score,
                    dense_score=dense_raw.get(chunk_id),
                    sparse_score=sparse_by_id.get(chunk_id),
                )
            )

        fused.sort(key=lambda rc: rc.score, reverse=True)
        return fused[:top_k]

    # ── Internals ────────────────────────────────────────────────
    @staticmethod
    def _bm25_scores(query: str, chunks: list, top_k: int) -> dict[str, float]:
        from rank_bm25 import BM25Okapi

        corpus = [_tokenize(chunk.content) for chunk in chunks]
        if not any(corpus):
            return {}
        bm25 = BM25Okapi(corpus)
        query_tokens = _tokenize(query)
        if not query_tokens:
            return {}
        raw_scores = bm25.get_scores(query_tokens)
        ranked = sorted(
            zip(chunks, raw_scores, strict=False), key=lambda pair: pair[1], reverse=True
        )
        limit = max(top_k, 1)
        return {
            chunk.id: float(score)
            for chunk, score in ranked[:limit]
            if score > 0.0
        }

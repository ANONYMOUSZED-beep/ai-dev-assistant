"""Cross-encoder reranking of retrieval candidates.

Wraps ``sentence_transformers.CrossEncoder``; the model is loaded lazily on the first
:meth:`rerank` call. Each returned chunk carries its ``rerank_score``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.schemas.rag import RetrievedChunk

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder


class CrossEncoderReranker:
    """Reranker implementation satisfying :class:`app.rag.contracts.Reranker`."""

    def __init__(self, model_name: str, *, batch_size: int = 32) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model: CrossEncoder | None = None

    def rerank(
        self, query: str, candidates: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        """Reorder ``candidates`` by cross-encoder relevance, keeping the best ``top_k``."""
        if not candidates:
            return []
        model = self._ensure_model()
        pairs = [[query, rc.chunk.content] for rc in candidates]
        scores = model.predict(
            pairs,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        reranked = [
            candidate.model_copy(update={"rerank_score": float(score)})
            for candidate, score in zip(candidates, scores, strict=False)
        ]
        reranked.sort(key=lambda rc: rc.rerank_score or 0.0, reverse=True)
        return reranked[:top_k]

    def warmup(self) -> None:
        """Eagerly load the model so the first real request isn't slowed by download/load."""
        self._ensure_model()

    # ── Internals ────────────────────────────────────────────────
    def _ensure_model(self) -> CrossEncoder:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name)
        return self._model

"""BGE dense embedder backed by sentence-transformers.

The underlying model is loaded lazily on the first embedding call so that importing
this module (and therefore ``app.main``) never triggers a model download.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class BGEEmbedder:
    """Embedder implementation satisfying :class:`app.rag.contracts.Embedder`.

    Produces L2-normalised embeddings so that inner-product search is equivalent to
    cosine similarity.
    """

    def __init__(self, model_name: str, *, batch_size: int = 32) -> None:
        self._model_name = model_name
        self._batch_size = batch_size
        self._model: SentenceTransformer | None = None
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        """Embedding dimensionality (loads the model on first access)."""
        if self._dimension is None:
            model = self._ensure_model()
            dim = model.get_sentence_embedding_dimension()
            if dim is None:
                raise RuntimeError(f"Model '{self._model_name}' reported no embedding dimension")
            self._dimension = int(dim)
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents into normalised dense vectors."""
        if not texts:
            return []
        model = self._ensure_model()
        vectors = model.encode(
            texts,
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.astype("float32").tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into a normalised dense vector."""
        model = self._ensure_model()
        vector = model.encode(
            [text],
            batch_size=1,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector[0].astype("float32").tolist()

    def warmup(self) -> None:
        """Eagerly load the model so the first real request isn't slowed by download/load."""
        self._ensure_model()

    # ── Internals ────────────────────────────────────────────────
    def _ensure_model(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            dim = self._model.get_sentence_embedding_dimension()
            self._dimension = int(dim) if dim is not None else None
        return self._model

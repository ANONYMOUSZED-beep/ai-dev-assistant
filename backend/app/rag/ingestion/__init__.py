"""Document ingestion: load raw sources into normalised :class:`Document` objects."""

from __future__ import annotations

from app.rag.ingestion.github import load_github_repo
from app.rag.ingestion.loaders import infer_source_type, load_by_uri
from app.schemas.rag import Document, SourceType

__all__ = ["load_source", "load_github_repo", "load_by_uri", "infer_source_type"]


def load_source(
    *,
    source_type: SourceType | None = None,
    uri: str | None = None,
    text: str | None = None,
    title: str | None = None,
) -> list[Document]:
    """Load a single source into documents.

    Exactly one of ``text`` or ``uri`` should be supplied. Raw ``text`` is wrapped
    directly; a ``uri`` is dispatched to the appropriate loader by type/extension/scheme.
    """
    if text is not None:
        resolved = source_type or SourceType.TXT
        source_id = uri or title or "inline-text"
        return [
            Document(
                content=text,
                source_type=resolved,
                source_id=source_id,
                title=title,
                uri=uri,
            )
        ]
    if uri:
        return load_by_uri(uri, source_type=source_type, title=title)
    raise ValueError("load_source requires either 'text' or 'uri'")

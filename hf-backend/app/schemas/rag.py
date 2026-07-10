"""Core RAG domain models.

These types form the contract between the ingestion, chunking, embedding, retrieval,
and citation components, and the services/API that consume them.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Origin of an ingested document."""

    PDF = "pdf"
    MARKDOWN = "markdown"
    HTML = "html"
    DOCX = "docx"
    TXT = "txt"
    CODE = "code"
    GITHUB = "github"
    WEB = "web"


class Document(BaseModel):
    """A normalised source document prior to chunking."""

    content: str
    source_type: SourceType
    # Stable identifier of the origin (file path, url, or "owner/repo:path").
    source_id: str
    title: str | None = None
    uri: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class Chunk(BaseModel):
    """A retrievable unit of text derived from a :class:`Document`."""

    id: str
    document_id: str
    content: str
    source_type: SourceType
    source_id: str
    title: str | None = None
    uri: str | None = None
    # Positional metadata (e.g. page, line range, symbol name) for precise citations.
    start_line: int | None = None
    end_line: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RetrievedChunk(BaseModel):
    """A chunk returned from retrieval with relevance scoring."""

    chunk: Chunk
    score: float
    # Optional component scores for transparency / debugging.
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None


class Citation(BaseModel):
    """A human-readable source reference attached to an answer."""

    index: int
    title: str
    source_type: SourceType
    uri: str | None = None
    snippet: str
    start_line: int | None = None
    end_line: int | None = None
    score: float | None = None

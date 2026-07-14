"""API request/response schemas for the application's features."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.rag import Citation, SourceType


# ── Chat (documentation) ─────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    collection: str = "docs"
    conversation_id: str | None = None
    stream: bool = False


class Answer(BaseModel):
    """A grounded answer with its supporting citations."""

    text: str
    citations: list[Citation] = Field(default_factory=list)
    model: str | None = None
    provider: str | None = None
    conversation_id: str | None = None
    follow_ups: list[str] = Field(default_factory=list)
    confidence: float | None = None


# ── Document ingestion ───────────────────────────────────────────
class IngestRequest(BaseModel):
    collection: str = "docs"
    uri: str | None = None
    source_type: SourceType | None = None
    text: str | None = None
    title: str | None = None


class IngestResponse(BaseModel):
    document_id: str
    collection: str
    chunks_indexed: int


# ── Repositories ─────────────────────────────────────────────────
class RepositoryCreateRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL or owner/repo")
    branch: str | None = None


class IndexStatus(str, Enum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class RepositoryResponse(BaseModel):
    id: str
    url: str
    branch: str | None = None
    status: IndexStatus
    files_indexed: int = 0
    chunks_indexed: int = 0
    error: str | None = None


class RepoChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation_id: str | None = None
    stream: bool = False


# ── Semantic code search ─────────────────────────────────────────
class CodeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    repository_id: str | None = None
    top_k: int = 10


class CodeSearchHit(BaseModel):
    path: str
    snippet: str
    start_line: int | None = None
    end_line: int | None = None
    score: float
    symbol: str | None = None


class CodeSearchResponse(BaseModel):
    query: str
    hits: list[CodeSearchHit] = Field(default_factory=list)


# ── Error debugging ──────────────────────────────────────────────
class DebugRequest(BaseModel):
    error: str = Field(..., min_length=1, description="Stack trace or error log")
    language: str | None = None
    code_context: str | None = None
    repository_id: str | None = None


# ── Pair programmer ──────────────────────────────────────────────
class PairAction(str, Enum):
    EXPLAIN = "explain"
    REFACTOR = "refactor"
    TEST = "test"
    DOCUMENT = "document"
    OPTIMIZE = "optimize"
    SECURITY = "security"


class PairRequest(BaseModel):
    action: PairAction
    code: str = Field(..., min_length=1)
    language: str | None = None
    instructions: str | None = None

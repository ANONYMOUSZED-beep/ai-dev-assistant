"""Schemas for persisted chat conversations and their messages."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import Citation

# The chat surface that produced a conversation. Used for the type badge in the UI.
ConversationKind = Literal["docs", "repo", "debug", "pair"]


class MessageOut(BaseModel):
    """A single stored message in a conversation."""

    id: str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class ConversationSummary(BaseModel):
    """Lightweight conversation record for the history list."""

    id: str
    kind: ConversationKind
    title: str | None = None
    collection: str | None = None
    repository_id: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    """A conversation with its full message history."""

    messages: list[MessageOut] = Field(default_factory=list)


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)


class ShareResponse(BaseModel):
    """Result of publishing a conversation as a public read-only link."""

    share_id: str
    url_path: str

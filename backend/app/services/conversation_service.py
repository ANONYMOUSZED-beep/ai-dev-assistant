"""Persistence and retrieval of chat conversations.

Conversations are scoped per user and tagged with a ``kind`` (docs/repo/debug/pair)
so the UI can group them and show a type badge. Every chat turn appends a user and an
assistant message, letting users revisit older chats.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from app.db.models import Conversation, Message
from app.schemas.conversation import (
    ConversationDetail,
    ConversationSummary,
    MessageOut,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.schemas.rag import Citation

_MAX_TITLE_LEN = 80


def _derive_title(text: str) -> str:
    """Build a short conversation title from the first user message."""
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= _MAX_TITLE_LEN:
        return cleaned or "New conversation"
    return cleaned[: _MAX_TITLE_LEN - 1].rstrip() + "…"


class ConversationService:
    """CRUD + turn persistence for chat conversations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Reads ────────────────────────────────────────────────────
    async def list_summaries(
        self, user_id: str, kind: str | None = None
    ) -> list[ConversationSummary]:
        """Return the user's conversations (newest first), optionally by kind."""
        count_col = func.count(Message.id)
        stmt = (
            select(Conversation, count_col)
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.user_id == user_id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
        )
        if kind is not None:
            stmt = stmt.where(Conversation.kind == kind)
        rows = (await self._session.execute(stmt)).all()
        return [self._to_summary(conv, count) for conv, count in rows]

    async def get_detail(
        self, user_id: str, conversation_id: str
    ) -> ConversationDetail | None:
        """Return one conversation with its messages, or None if not owned/found."""
        conv = await self._session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            return None
        return await self._detail_for(conv)

    async def get_by_share_id(self, share_id: str) -> ConversationDetail | None:
        """Return a conversation by its public share token (NO owner check).

        This powers the public, unauthenticated read-only share view.
        """
        conv = (
            await self._session.execute(
                select(Conversation).where(Conversation.share_id == share_id)
            )
        ).scalar_one_or_none()
        if conv is None:
            return None
        return await self._detail_for(conv)

    # ── Writes ───────────────────────────────────────────────────
    async def create(
        self,
        *,
        user_id: str,
        kind: str,
        title: str | None = None,
        collection: str | None = None,
        repository_id: str | None = None,
    ) -> Conversation:
        conv = Conversation(
            user_id=user_id,
            kind=kind,
            title=title,
            collection=collection,
            repository_id=repository_id,
        )
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def resolve(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        kind: str,
        first_message: str,
        collection: str | None = None,
        repository_id: str | None = None,
    ) -> Conversation:
        """Return the referenced conversation (if owned) or create a new one.

        A new conversation's title is derived from the first user message.
        """
        if conversation_id:
            conv = await self._session.get(Conversation, conversation_id)
            if conv is not None and conv.user_id == user_id:
                return conv
        return await self.create(
            user_id=user_id,
            kind=kind,
            title=_derive_title(first_message),
            collection=collection,
            repository_id=repository_id,
        )

    async def add_message(
        self,
        conversation: Conversation,
        role: str,
        content: str,
        citations: list[Citation] | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            citations=[c.model_dump(mode="json") for c in (citations or [])],
        )
        self._session.add(msg)
        return msg

    async def record_turn(
        self,
        *,
        user_id: str,
        conversation_id: str | None,
        kind: str,
        question: str,
        answer_text: str,
        citations: list[Citation] | None = None,
        collection: str | None = None,
        repository_id: str | None = None,
    ) -> str:
        """Persist a full user→assistant turn and return the conversation id."""
        conv = await self.resolve(
            user_id=user_id,
            conversation_id=conversation_id,
            kind=kind,
            first_message=question,
            collection=collection,
            repository_id=repository_id,
        )
        await self.add_message(conv, "user", question)
        await self.add_message(conv, "assistant", answer_text, citations)
        await self._session.commit()
        return conv.id

    async def share(self, user_id: str, conversation_id: str) -> str | None:
        """Publish a conversation and return its share token (idempotent).

        Returns None if the conversation is not owned by ``user_id``. If it already
        has a share token, that same token is returned; otherwise a new one is
        generated and persisted.
        """
        conv = await self._session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            return None
        if not conv.share_id:
            conv.share_id = secrets.token_urlsafe(16)
            await self._session.commit()
        return conv.share_id

    async def unshare(self, user_id: str, conversation_id: str) -> bool:
        """Revoke a conversation's public share link. Returns False if not owned."""
        conv = await self._session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            return False
        conv.share_id = None
        await self._session.commit()
        return True

    async def delete(self, user_id: str, conversation_id: str) -> bool:
        conv = await self._session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            return False
        await self._session.delete(conv)
        await self._session.commit()
        return True

    async def rename(
        self, user_id: str, conversation_id: str, title: str
    ) -> ConversationSummary | None:
        conv = await self._session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user_id:
            return None
        conv.title = title
        await self._session.commit()
        count = (
            await self._session.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conversation_id
                )
            )
        ).scalar_one()
        return self._to_summary(conv, count)

    # ── Helpers ──────────────────────────────────────────────────
    async def _detail_for(self, conv: Conversation) -> ConversationDetail:
        """Build a ConversationDetail (summary + full message history) for ``conv``."""
        messages = (
            await self._session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
            )
        ).scalars().all()
        summary = self._to_summary(conv, len(messages))
        return ConversationDetail(
            **summary.model_dump(),
            messages=[
                MessageOut(
                    id=m.id,
                    role=m.role,  # type: ignore[arg-type]
                    content=m.content,
                    citations=m.citations or [],
                    created_at=m.created_at,
                )
                for m in messages
            ],
        )

    @staticmethod
    def _to_summary(conv: Conversation, message_count: int) -> ConversationSummary:
        return ConversationSummary(
            id=conv.id,
            kind=conv.kind,  # type: ignore[arg-type]
            title=conv.title,
            collection=conv.collection,
            repository_id=conv.repository_id,
            message_count=message_count,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

"""FastAPI dependency providers.

Engines (RAG pipeline, LLM provider) are constructed once during the application
lifespan and stored on ``app.state``; these helpers expose them to routes/services.
DB sessions and the Redis cache are provided per-request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import RedisCache, get_redis
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.llm.base import BaseLLMProvider
from app.rag.pipeline import RagPipeline

if TYPE_CHECKING:
    from app.db.models import User


async def get_current_user(
    request: Request, session: Annotated[AsyncSession, Depends(get_session)]
) -> User:
    """Resolve the authenticated user from a ``Authorization: Bearer <jwt>`` header.

    Raises :class:`AuthError` (401) when the token is missing, invalid, expired, or
    refers to a user that no longer exists.
    """
    from app.core.auth import decode_token
    from app.core.exceptions import AuthError
    from app.db.models import User

    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise AuthError("Missing or invalid Authorization header")

    user_id = decode_token(token.strip())
    if user_id is None:
        raise AuthError("Invalid or expired token")

    user = await session.get(User, user_id)
    if user is None:
        raise AuthError("User no longer exists")
    return user


def forbid_guest(user: CurrentUserDep) -> None:
    """Reject guest (demo) accounts on routes that write to shared state.

    Guests are read-only against the seeded knowledge base; ingestion and repository
    indexing write into the shared vector store, so they must require a real account.
    """
    from app.core.exceptions import AuthError

    if getattr(user, "is_guest", False):
        raise AuthError("Create a free account to use this feature.")


def get_rag_pipeline(request: Request) -> RagPipeline:
    """Return the shared RAG pipeline created at startup."""
    return request.app.state.rag_pipeline


def get_llm(request: Request) -> BaseLLMProvider:
    """Return the shared LLM provider created at startup."""
    return request.app.state.llm_provider


async def get_cache() -> AsyncGenerator[RedisCache, None]:
    """Provide a Redis cache wrapper."""
    yield RedisCache(get_redis())


# Reusable annotated dependencies for concise route signatures.
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[RedisCache, Depends(get_cache)]
RagDep = Annotated[RagPipeline, Depends(get_rag_pipeline)]
LLMDep = Annotated[BaseLLMProvider, Depends(get_llm)]
CurrentUserDep = Annotated["User", Depends(get_current_user)]

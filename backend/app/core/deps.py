"""FastAPI dependency providers.

Engines (RAG pipeline, LLM provider) are constructed once during the application
lifespan and stored on ``app.state``; these helpers expose them to routes/services.
DB sessions and the Redis cache are provided per-request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import RedisCache, get_redis
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.llm.base import BaseLLMProvider
from app.rag.pipeline import RagPipeline


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

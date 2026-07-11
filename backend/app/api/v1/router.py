"""Aggregate router mounting all v1 feature routes.

``health`` and ``auth`` are public. Every other router requires an authenticated
user (``Authorization: Bearer <jwt>``) and is rate limited.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1 import (
    auth,
    chat,
    conversations,
    debug,
    documents,
    health,
    pair,
    repositories,
    search,
)
from app.core.deps import get_current_user
from app.core.security import enforce_rate_limit

api_router = APIRouter()

# Public routers.
api_router.include_router(health.router)
api_router.include_router(auth.router)

# Protected: require a valid JWT and apply rate limiting.
_guarded = [Depends(get_current_user), Depends(enforce_rate_limit)]
for feature in (chat, conversations, documents, repositories, search, debug, pair):
    api_router.include_router(feature.router, dependencies=_guarded)

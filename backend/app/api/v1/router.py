"""Aggregate router mounting all v1 feature routes.

``health`` is intentionally public (used by load balancers / probes). Every other
router is guarded by API-key authentication and per-client rate limiting.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import chat, debug, documents, health, pair, repositories, search
from app.core.security import auth_and_rate_limit_dependencies

api_router = APIRouter()

# Public: liveness / readiness probes.
api_router.include_router(health.router)

# Protected: data + AI endpoints require a valid API key and are rate limited.
_guarded = auth_and_rate_limit_dependencies()
for feature in (chat, documents, repositories, search, debug, pair):
    api_router.include_router(feature.router, dependencies=_guarded)

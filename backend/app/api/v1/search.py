"""Semantic code search endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import RagDep
from app.schemas.chat import CodeSearchRequest, CodeSearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/code", response_model=CodeSearchResponse)
async def search_code(req: CodeSearchRequest, rag: RagDep) -> CodeSearchResponse:
    """Natural-language semantic search over indexed code."""
    service = SearchService(rag)
    return await service.search(req.query, req.repository_id, req.top_k)

"""Error / stack-trace debugging endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import LLMDep, RagDep
from app.schemas.chat import Answer, DebugRequest
from app.services.debug_service import DebugService

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("", response_model=Answer)
async def debug(req: DebugRequest, rag: RagDep, llm: LLMDep) -> Answer:
    """Analyse an error/stack trace and return corrected code with citations."""
    service = DebugService(rag, llm)
    return await service.debug(req.error, req.language, req.code_context, req.repository_id)

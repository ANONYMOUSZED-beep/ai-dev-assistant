"""AI pair-programmer endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import LLMDep, RagDep
from app.schemas.chat import Answer, PairRequest
from app.services.pair_service import PairService

router = APIRouter(prefix="/pair", tags=["pair"])


@router.post("", response_model=Answer)
async def pair(req: PairRequest, rag: RagDep, llm: LLMDep) -> Answer:
    """Run a pair-programming action (explain/refactor/test/document/optimize/security)."""
    service = PairService(rag, llm)
    return await service.run(req.action, req.code, req.language, req.instructions)

from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import MemoRequest, MemoResponse
from backend.services.memo_service import generate

router = APIRouter()


@router.post("/memo", response_model=MemoResponse)
def post_memo(payload: MemoRequest) -> dict:
    return generate(payload.loop_id, use_llm=False)


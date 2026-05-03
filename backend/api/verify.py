from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import VerifyRequest, VerifyResponse
from backend.services.verify_service import verify

router = APIRouter()


@router.post("/verify", response_model=VerifyResponse)
def post_verify(payload: VerifyRequest) -> dict:
    return verify(payload.loop_id, payload.memo)


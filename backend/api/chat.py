from __future__ import annotations

from fastapi import APIRouter

from backend.schemas import ChatRequest, ChatResponse
from backend.services.chat_service import ask

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def post_chat(payload: ChatRequest) -> dict:
    return ask(payload.message, payload.selected_loop_id)


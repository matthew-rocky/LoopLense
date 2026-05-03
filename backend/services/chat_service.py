from __future__ import annotations

from typing import Any

from src.chat import PROMPTS, handle_prompt

from backend.services.loop_service import clean_value, selected_context


def ask(message: str, selected_loop_id: str | None = None) -> dict[str, Any]:
    ctx = selected_context(selected_loop_id)
    response = handle_prompt(message, ctx, selected_loop_id=ctx.get("selected_loop_id"))
    followups = response.get("suggested_followups") or PROMPTS[:5]
    return clean_value(
        {
            "answer": response.get("content", ""),
            "intent": response.get("intent", "unsupported"),
            "data": response.get("data") or [],
            "evidence": response.get("evidence") or [],
            "suggested_followups": followups,
            "chart": response.get("chart"),
            "verification": response.get("verification"),
            "memo_verification": response.get("memo_verification"),
            "method": response.get("sql"),
            "memo": response.get("memo"),
        }
    )

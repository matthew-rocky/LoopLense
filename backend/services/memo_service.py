from __future__ import annotations

from typing import Any

from src.memo import DISCLAIMER
from src.verify import build_memo

from backend.services.loop_service import clean_value, loop_detail


def generate(loop_id: str, use_llm: bool = False) -> dict[str, Any]:
    detail = loop_detail(loop_id)
    result = build_memo(detail["loop"], detail["edges"], detail["people"], use_llm=use_llm)
    return clean_value({**result, "disclaimer": result["memo"].get("disclaimer", DISCLAIMER)})


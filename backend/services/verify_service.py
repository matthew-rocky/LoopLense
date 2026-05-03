from __future__ import annotations

from typing import Any

from src.verify import verify_memo

from backend.services.loop_service import clean_value, loop_detail


def verify(loop_id: str, memo: str | dict[str, Any]) -> dict[str, Any]:
    detail = loop_detail(loop_id)
    result = verify_memo(memo, detail["loop"], detail["people"], detail["edges"], [])
    warnings = [
        str(check.get("explanation") or check.get("claim"))
        for check in result.get("checks", [])
        if str(check.get("status", "")).lower() in {"warning", "failed", "mismatch", "not found", "partially supported"}
    ]
    return clean_value({"final_status": result.get("overall_status", "Needs review"), "verification": result, "warnings": warnings})


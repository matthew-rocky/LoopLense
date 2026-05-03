from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    selected_loop_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    intent: str
    data: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    suggested_followups: list[str] = []
    chart: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    memo: dict[str, Any] | None = None
    memo_verification: dict[str, Any] | None = None
    method: str | None = None


class MemoRequest(BaseModel):
    loop_id: str


class MemoResponse(BaseModel):
    memo: dict[str, Any]
    checks: list[dict[str, Any]]
    safe: bool
    disclaimer: str


class VerifyRequest(BaseModel):
    loop_id: str
    memo: str | dict[str, Any]


class VerifyResponse(BaseModel):
    final_status: str
    verification: dict[str, Any]
    warnings: list[str] = []

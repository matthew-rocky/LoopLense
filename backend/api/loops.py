from __future__ import annotations

from fastapi import APIRouter, Query

from backend.services.graph_service import network
from backend.services.loop_service import list_loops, loop_detail, summary

router = APIRouter()


@router.get("/summary")
def get_summary() -> dict:
    return summary()


@router.get("/loops")
def get_loops(
    label: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    min_flow: float | None = None,
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = None,
) -> list[dict]:
    return list_loops(label=label, min_score=min_score, max_score=max_score, min_flow=min_flow, limit=limit, search=search)


@router.get("/loops/{loop_id}")
def get_loop_detail(loop_id: str) -> dict:
    return loop_detail(loop_id)


@router.get("/loops/{loop_id}/network")
def get_loop_network(loop_id: str) -> dict:
    return network(loop_id)


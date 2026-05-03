from __future__ import annotations

from fastapi import APIRouter

from backend.services.loop_service import health

router = APIRouter()


@router.get("/health")
def get_health() -> dict:
    return health()


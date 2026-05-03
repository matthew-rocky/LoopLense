from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat, health, loops, memo, verify

app = FastAPI(
    title="LoopLens API",
    version="1.0.0",
    description="Evidence-grounded API for circular charity funding review workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api"
app.include_router(health.router, prefix=api_prefix, tags=["health"])
app.include_router(loops.router, prefix=api_prefix, tags=["loops"])
app.include_router(chat.router, prefix=api_prefix, tags=["chat"])
app.include_router(memo.router, prefix=api_prefix, tags=["memo"])
app.include_router(verify.router, prefix=api_prefix, tags=["verify"])


@app.get("/")
def root() -> dict[str, str]:
    return {"project": "LoopLens", "status": "ok", "docs": "/docs"}


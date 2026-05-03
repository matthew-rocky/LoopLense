from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api import chat, health, loops, memo, verify

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_OUT = PROJECT_ROOT / "frontend" / "out"

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

next_assets = FRONTEND_OUT / "_next"
if next_assets.exists():
    app.mount("/_next", StaticFiles(directory=next_assets), name="next-static")

@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    if not FRONTEND_OUT.exists():
        return JSONResponse(
            {
                "project": "LoopLens",
                "status": "backend running",
                "docs": "/docs",
                "frontend": "missing",
                "message": "frontend/out was not found. Run `cd frontend && npm install && npm run build` before serving the full app.",
            },
            status_code=200,
        )

    requested = (FRONTEND_OUT / full_path).resolve()
    try:
        requested.relative_to(FRONTEND_OUT)
    except ValueError:
        requested = FRONTEND_OUT / "index.html"

    if requested.is_file():
        return FileResponse(requested)

    html_file = FRONTEND_OUT / f"{full_path}.html"
    if html_file.is_file():
        return FileResponse(html_file)

    index_file = FRONTEND_OUT / full_path / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    # Static export cannot generate arbitrary dynamic loop detail files. Serve
    # the exported client detail page so direct refreshes for /loops/{id} work.
    parts = [part for part in full_path.split("/") if part]
    if len(parts) == 2 and parts[0] == "loops":
        loop_detail = FRONTEND_OUT / "loops" / "detail.html"
        if loop_detail.is_file():
            return FileResponse(loop_detail)

    return FileResponse(FRONTEND_OUT / "index.html")

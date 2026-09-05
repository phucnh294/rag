"""FastAPI app: wires up routes and serves the UI. Wiring only.

GET / -> ui/index.html
POST /upload -> routes_upload.router
POST /chat -> routes_chat.router
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from api.routes_chat import router as chat_router
from api.routes_upload import router as upload_router

app = FastAPI(title="RAG Lab")
app.include_router(upload_router)
app.include_router(chat_router)

_UI_INDEX = Path(__file__).parent.parent / "ui" / "index.html"


@app.get("/")
def serve_ui_martin() -> FileResponse:
    """Serve the static chat + upload UI."""
    return FileResponse(_UI_INDEX)

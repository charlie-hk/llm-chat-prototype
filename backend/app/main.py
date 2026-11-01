import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.providers.base import ProviderError
from app.providers.factory import build_provider
from app.schemas import ChatRequest

log = logging.getLogger("uvicorn.error")

settings = get_settings()
provider = build_provider(settings)

app = FastAPI(title="LLM Chat Prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


# Light per-IP rate limit so a public demo can't exhaust the free quota.
_hits: dict[str, deque] = defaultdict(deque)


def rate_limited(ip: str) -> bool:
    now = time.monotonic()
    window, limit = 60.0, settings.rate_limit_per_min
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    # The UI shows which provider/model is live.
    return {"provider": provider.name, "model": settings.model or None}


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    if rate_limited(client):
        return JSONResponse(
            {"detail": "Too many messages, slow down a little and try again."},
            status_code=429,
        )

    # Keep only the most recent turns so the context sent to the model stays bounded.
    history = req.messages[-settings.max_history :]

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for token in provider.stream(settings.system_prompt, history):
                yield sse({"type": "token", "value": token})
            yield sse({"type": "done"})
        except ProviderError as e:
            log.warning("provider error: %s", e)
            yield sse({"type": "error", "message": str(e) or "Provider error (see server logs)."})
        except Exception as e:
            log.exception("unexpected error in chat stream")
            yield sse({"type": "error", "message": f"Server error: {e.__class__.__name__}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Serve the built frontend from the same origin when it is present (production /
# single-container deploys). In local dev the Vite server handles the UI instead.
_static = Path(settings.static_dir)
if _static.is_dir():
    app.mount("/assets", StaticFiles(directory=_static / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(_static / "index.html")

    @app.get("/{path:path}")
    def spa(path: str):
        target = _static / path
        if target.is_file():
            return FileResponse(target)
        return FileResponse(_static / "index.html")

import json
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.providers.base import ProviderError
from app.providers.factory import build_provider
from app.schemas import ChatRequest

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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/config")
def config():
    # The UI shows which provider/model is live.
    return {"provider": provider.name, "model": settings.model or None}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    # Keep only the most recent turns so the context sent to the model stays bounded.
    history = req.messages[-settings.max_history :]

    async def event_stream() -> AsyncIterator[str]:
        try:
            async for token in provider.stream(settings.system_prompt, history):
                yield sse({"type": "token", "value": token})
            yield sse({"type": "done"})
        except ProviderError as e:
            yield sse({"type": "error", "message": str(e)})
        except Exception:
            yield sse({"type": "error", "message": "Unexpected server error."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

import asyncio
import json
from collections.abc import AsyncIterator

from app.providers.base import LLMProvider, ProviderError
from app.schemas import Message

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"

# 404: model not available to this key. 429/500/503: temporarily overloaded.
# Both reasons mean "try the next model in the chain".
SKIP_TO_NEXT = {404, 429, 500, 503}
MAX_ATTEMPTS = 2  # per model, for transient overload


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError("Gemini selected but API_KEY is empty.")
        self._key = api_key
        # MODEL may be a comma-separated fallback chain. First that works wins.
        self._models = [m.strip() for m in (model or "gemini-flash-lite-latest").split(",") if m.strip()]

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        import httpx

        body: dict = {
            "contents": [
                {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
                for m in messages
            ]
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}

        headers = {"x-goog-api-key": self._key, "content-type": "application/json"}
        timeout = httpx.Timeout(60.0, connect=10.0)
        last_error = "No Gemini model was available."

        for model in self._models:
            url = ENDPOINT.format(model=model)
            for attempt in range(MAX_ATTEMPTS):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        async with client.stream("POST", url, headers=headers, json=body) as resp:
                            if resp.status_code in SKIP_TO_NEXT:
                                body_text = (await resp.aread()).decode(errors="replace")[:200]
                                last_error = f"Gemini {resp.status_code} on {model}: {body_text}"
                                if resp.status_code in (429, 500, 503) and attempt < MAX_ATTEMPTS - 1:
                                    await asyncio.sleep(1.0 * (attempt + 1))
                                    continue
                                break  # move to next model
                            if resp.status_code != 200:
                                detail = (await resp.aread()).decode(errors="replace")[:300]
                                raise ProviderError(f"Gemini {resp.status_code}: {detail}")
                            async for line in resp.aiter_lines():
                                line = line.strip()
                                if not line.startswith("data:"):
                                    continue
                                payload = line[5:].strip()
                                if not payload:
                                    continue
                                data = json.loads(payload)
                                for cand in data.get("candidates", []):
                                    for part in cand.get("content", {}).get("parts", []):
                                        text = part.get("text")
                                        if text:
                                            yield text
                            return  # streamed successfully
                except ProviderError:
                    raise
                except httpx.TimeoutException:
                    last_error = f"Gemini timed out on {model}."
                    if attempt < MAX_ATTEMPTS - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))
                        continue
                    break  # move to next model
                except Exception as e:
                    raise ProviderError(f"{e.__class__.__name__}: {e}".strip(": ")) from e

        raise ProviderError(last_error)

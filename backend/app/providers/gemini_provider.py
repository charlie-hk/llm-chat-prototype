import json
from collections.abc import AsyncIterator

from app.providers.base import LLMProvider, ProviderError
from app.schemas import Message

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError("Gemini selected but API_KEY is empty.")
        self._key = api_key
        self._model = model or "gemini-2.0-flash"

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        import httpx

        url = ENDPOINT.format(model=self._model)
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

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
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
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(str(e)) from e

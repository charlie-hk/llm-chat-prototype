from collections.abc import AsyncIterator

from app.providers.base import LLMProvider, ProviderError
from app.schemas import Message


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError("Gemini selected but API_KEY is empty.")
        try:
            import google.generativeai as genai
        except ImportError as e:
            raise ProviderError(
                "google-generativeai not installed. pip install google-generativeai"
            ) from e
        genai.configure(api_key=api_key)
        self._model_name = model or "gemini-1.5-flash"
        self._genai = genai

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        # Gemini uses "model" for the assistant role and carries history on the chat.
        model = self._genai.GenerativeModel(self._model_name, system_instruction=system)
        history = [
            {"role": "model" if m.role == "assistant" else "user", "parts": [m.content]}
            for m in messages[:-1]
        ]
        last = messages[-1].content
        try:
            chat = model.start_chat(history=history)
            # The SDK stream is synchronous; iterate it without blocking the loop.
            response = await _run(lambda: chat.send_message(last, stream=True))
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            raise ProviderError(str(e)) from e


async def _run(fn):
    import asyncio

    return await asyncio.to_thread(fn)

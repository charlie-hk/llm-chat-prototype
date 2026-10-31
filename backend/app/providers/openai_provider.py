from collections.abc import AsyncIterator

from app.providers.base import LLMProvider, ProviderError
from app.schemas import Message


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError("OpenAI selected but API_KEY is empty.")
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise ProviderError("openai package not installed. pip install openai") from e
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model or "gpt-4o-mini"

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        payload = [{"role": "system", "content": system}]
        payload += [{"role": m.role, "content": m.content} for m in messages]
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise ProviderError(str(e)) from e

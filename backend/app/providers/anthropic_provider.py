from collections.abc import AsyncIterator

from app.providers.base import LLMProvider, ProviderError
from app.schemas import Message


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ProviderError("Anthropic selected but API_KEY is empty.")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise ProviderError("anthropic package not installed. pip install anthropic") from e
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model or "claude-3-5-sonnet-latest"

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        try:
            async with self._client.messages.stream(
                model=self._model,
                system=system,
                max_tokens=1024,
                messages=payload,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise ProviderError(str(e)) from e

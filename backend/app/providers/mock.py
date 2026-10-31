import asyncio
from collections.abc import AsyncIterator

from app.providers.base import LLMProvider
from app.schemas import Message


class MockProvider(LLMProvider):
    """Streams a canned reply so the app runs with no API key.

    Useful for local dev, UI work, and tests. The timing mimics a real
    provider so the streaming UI behaves the same way.
    """

    name = "mock"

    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        reply = (
            "This is the mock provider, so there is no real model behind it yet. "
            "Set PROVIDER and an API_KEY in .env to switch to OpenAI, Anthropic or "
            f'Gemini. You said: "{last_user.strip()[:200]}".'
        )
        for word in reply.split(" "):
            await asyncio.sleep(0.03)
            yield word + " "

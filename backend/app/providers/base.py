from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.schemas import Message


class ProviderError(RuntimeError):
    """Raised when a provider can't be reached or is misconfigured."""


class LLMProvider(ABC):
    """One chat turn, streamed token by token.

    The system prompt is passed separately because each vendor wants it in a
    different place (OpenAI as a message, Anthropic as a top-level field).
    """

    name: str

    @abstractmethod
    async def stream(self, system: str, messages: list[Message]) -> AsyncIterator[str]:
        ...

from app.config import Settings
from app.providers.base import LLMProvider, ProviderError


def build_provider(settings: Settings) -> LLMProvider:
    provider = settings.provider.lower()

    if provider == "mock":
        from app.providers.mock import MockProvider

        return MockProvider()
    if provider == "openai":
        from app.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(settings.api_key, settings.model)
    if provider == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.api_key, settings.model)
    if provider == "gemini":
        from app.providers.gemini_provider import GeminiProvider

        return GeminiProvider(settings.api_key, settings.model)

    raise ProviderError(f"Unknown provider: {settings.provider!r}")

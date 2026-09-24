from social_media_agent.config.settings import settings
from social_media_agent.services.llm.base import LLMProvider
from social_media_agent.services.llm.ollama_provider import OllamaProvider


def get_llm_provider() -> LLMProvider:

    providers = {
        "ollama": OllamaProvider,
    }

    provider_class = providers.get(settings.llm_provider.lower())

    if provider_class is None:
        raise ValueError(
            f"Unsupported LLM provider: {settings.llm_provider}"
        )

    return provider_class()
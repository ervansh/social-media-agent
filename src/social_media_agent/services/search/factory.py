from social_media_agent.config.settings import settings
from social_media_agent.services.search.base import SearchProvider
from social_media_agent.services.search.ddgs_provider import (
    DDGSSearchProvider,
)


def get_search_provider() -> SearchProvider:

    providers = {
        "ddgs": DDGSSearchProvider,
    }

    provider_class = providers.get(
        settings.search_provider.lower()
    )

    if provider_class is None:
        raise ValueError(
            f"Unsupported search provider: "
            f"{settings.search_provider}"
        )

    return provider_class()
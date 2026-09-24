from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.base import (
    ImageProvider,
)
from social_media_agent.services.image.disabled_provider import (
    DisabledImageProvider,
)
from social_media_agent.services.image.development_provider import (
    DevelopmentImageProvider,
)
from social_media_agent.services.image.openai_provider import (
    OpenAIImageProvider,
)


def get_image_provider() -> ImageProvider:

    providers = {
        "disabled": DisabledImageProvider,
        "development": DevelopmentImageProvider,
        "openai": OpenAIImageProvider,
    }

    provider_class = providers.get(
        settings.image_provider.lower()
    )

    if provider_class is None:
        raise ValueError(
            "Unsupported image provider: "
            f"{settings.image_provider}"
        )

    return provider_class()
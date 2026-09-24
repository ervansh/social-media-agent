from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.publishing.media_url_resolver import (
    PublicBaseUrlMediaUrlResolver,
)
from social_media_agent.services.publishing.s3_media_url_resolver import (
    S3MediaUrlResolver,
)


def get_media_url_resolver():

    provider = (
        settings.media_url_provider
        .strip()
        .lower()
    )

    if provider == "public_base_url":
        return PublicBaseUrlMediaUrlResolver()

    if provider == "s3":
        return S3MediaUrlResolver()

    raise ValueError(
        "Unsupported MEDIA_URL_PROVIDER: "
        f"{settings.media_url_provider}"
    )

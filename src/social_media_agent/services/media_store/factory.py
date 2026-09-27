from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.media_store.local_store import (
    LocalMediaStore,
)
from social_media_agent.services.media_store.s3_store import (
    S3MediaStore,
)


def get_media_store():

    provider = (
        settings.media_store_provider
        .strip()
        .lower()
    )

    if provider == "local":
        return LocalMediaStore()

    if provider == "s3":
        return S3MediaStore()

    raise ValueError(
        "Unsupported MEDIA_STORE_PROVIDER: "
        f"{settings.media_store_provider}"
    )

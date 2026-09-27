from typing import Protocol
from urllib.parse import quote

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.media_store.path_utils import (
    normalize_storage_key,
)


class MediaUrlResolver(Protocol):

    def resolve(
        self,
        storage_key: str,
    ) -> str:
        ...


class PublicBaseUrlMediaUrlResolver:

    PROVIDER_NAME = "public_base_url"

    def __init__(
        self,
        base_url: str | None = None,
    ):
        self.base_url = (
            base_url
            if base_url is not None
            else settings.public_media_base_url
        )

    def resolve(
        self,
        storage_key: str,
    ) -> str:

        if not self.base_url:
            raise ValueError(
                "PUBLIC_MEDIA_BASE_URL is required "
                "for public-base-url media delivery."
            )

        normalized = normalize_storage_key(
            storage_key
        )

        encoded_key = "/".join(
            quote(
                part,
                safe="-._~",
            )
            for part
            in normalized.split("/")
        )

        return (
            f"{self.base_url.rstrip('/')}/"
            f"{encoded_key}"
        )

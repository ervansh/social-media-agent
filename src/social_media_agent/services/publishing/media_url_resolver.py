import re
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import quote

from social_media_agent.config.settings import (
    settings,
)


class MediaUrlResolver(Protocol):

    def resolve(
        self,
        storage_key: str,
    ) -> str:
        ...


def normalize_storage_key(
    storage_key: str,
) -> str:

    if not storage_key or not storage_key.strip():
        raise ValueError(
            "Media storage key cannot be empty."
        )

    raw_key = storage_key.strip()

    if (
        raw_key.startswith(("/", "\\"))
        or re.match(
            r"^[a-zA-Z]:[\\/]",
            raw_key,
        )
        or "://" in raw_key
    ):
        raise ValueError(
            "Media storage key must be a "
            "relative storage key."
        )

    normalized = raw_key.replace(
        "\\",
        "/",
    )

    parts = PurePosixPath(
        normalized
    ).parts

    if (
        not parts
        or any(
            part in {"", ".", ".."}
            for part in parts
        )
    ):
        raise ValueError(
            "Media storage key contains "
            "an invalid path segment."
        )

    return "/".join(parts)


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
            for part in normalized.split("/")
        )

        return (
            f"{self.base_url.rstrip('/')}/"
            f"{encoded_key}"
        )

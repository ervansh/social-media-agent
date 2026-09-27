from typing import Protocol

from social_media_agent.models.stored_media import (
    StoredMediaAsset,
)


class MediaStore(Protocol):

    PROVIDER_NAME: str

    def verify_access(
        self,
    ) -> None:
        ...

    def store(
        self,
        storage_key: str,
    ) -> StoredMediaAsset:
        ...

    def create_download_url(
        self,
        media: StoredMediaAsset,
    ) -> str:
        ...

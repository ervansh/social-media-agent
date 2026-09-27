from pathlib import Path
from typing import Any

from social_media_agent.services.media_store.s3_store import (
    S3MediaStore,
)


class S3MediaUrlResolver:

    PROVIDER_NAME = "s3"

    def __init__(
        self,
        *,
        bucket: str | None = None,
        region: str | None = None,
        prefix: str | None = None,
        local_root: str | Path | None = None,
        expires_in_seconds: int | None = None,
        endpoint_url: str | None = None,
        client: Any | None = None,
        media_store: S3MediaStore | None = None,
    ):
        self.media_store = (
            media_store
            if media_store is not None
            else S3MediaStore(
                bucket=bucket,
                region=region,
                prefix=prefix,
                local_root=local_root,
                expires_in_seconds=(
                    expires_in_seconds
                ),
                endpoint_url=endpoint_url,
                client=client,
            )
        )

    @property
    def bucket(
        self,
    ) -> str:

        return self.media_store.bucket

    def verify_access(
        self,
    ) -> None:

        self.media_store.verify_access()

    def resolve(
        self,
        storage_key: str,
    ) -> str:

        stored = (
            self.media_store.store(
                storage_key
            )
        )

        return (
            self.media_store
            .create_download_url(
                stored
            )
        )

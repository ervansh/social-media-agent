import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.publishing.media_url_resolver import (
    normalize_storage_key,
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
    ):
        self.bucket = (
            bucket
            if bucket is not None
            else settings.media_s3_bucket
        )

        self.region = (
            region
            if region is not None
            else settings.media_s3_region
        )

        self.prefix = (
            prefix
            if prefix is not None
            else settings.media_s3_prefix
        ).strip("/")

        self.local_root = Path(
            local_root
            if local_root is not None
            else settings.generated_assets_dir
        ).resolve()

        self.expires_in_seconds = (
            expires_in_seconds
            if expires_in_seconds is not None
            else settings
            .media_s3_presigned_url_expiry_seconds
        )

        self.endpoint_url = (
            endpoint_url
            if endpoint_url is not None
            else settings.media_s3_endpoint_url
        )

        if not self.bucket:
            raise ValueError(
                "MEDIA_S3_BUCKET is required "
                "when MEDIA_URL_PROVIDER=s3."
            )

        if self.expires_in_seconds <= 0:
            raise ValueError(
                "MEDIA_S3_PRESIGNED_URL_EXPIRY_SECONDS "
                "must be greater than zero."
            )

        self.client = (
            client
            if client is not None
            else self._build_client()
        )

    def verify_access(
        self,
    ) -> None:

        try:
            self.client.head_bucket(
                Bucket=self.bucket
            )

        except Exception as exc:
            raise RuntimeError(
                "S3 bucket preflight failed. "
                f"Bucket='{self.bucket}'. "
                "Verify AWS credentials, region, "
                "bucket name, and s3:ListBucket "
                "permission."
            ) from exc

    def resolve(
        self,
        storage_key: str,
    ) -> str:

        normalized = normalize_storage_key(
            storage_key
        )

        local_path = (
            self.local_root
            / Path(*normalized.split("/"))
        ).resolve()

        self._ensure_inside_root(
            local_path
        )

        if not local_path.is_file():
            raise FileNotFoundError(
                "Generated media file not found: "
                f"{local_path}"
            )

        object_key = self._object_key(
            normalized
        )

        content_type = (
            mimetypes.guess_type(
                local_path.name
            )[0]
            or "application/octet-stream"
        )

        self.client.upload_file(
            str(local_path),
            self.bucket,
            object_key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
            },
            ExpiresIn=(
                self.expires_in_seconds
            ),
        )

        if not url:
            raise RuntimeError(
                "S3 did not return a presigned "
                "media URL."
            )

        return str(url)

    def _object_key(
        self,
        normalized_storage_key: str,
    ) -> str:

        key = str(
            PurePosixPath(
                normalized_storage_key
            )
        )

        if not self.prefix:
            return key

        return str(
            PurePosixPath(
                self.prefix,
                key,
            )
        )

    def _ensure_inside_root(
        self,
        local_path: Path,
    ) -> None:

        try:
            local_path.relative_to(
                self.local_root
            )

        except ValueError as exc:
            raise ValueError(
                "Resolved media path escapes "
                "GENERATED_ASSETS_DIR."
            ) from exc

    def _build_client(
        self,
    ):

        try:
            import boto3
            from botocore.config import Config

        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for S3 media "
                "delivery. Install with: "
                "pip install -e \".[aws]\""
            ) from exc

        kwargs = {}

        if self.region:
            kwargs[
                "region_name"
            ] = self.region

        if self.endpoint_url:
            kwargs[
                "endpoint_url"
            ] = self.endpoint_url

        else:
            kwargs[
                "config"
            ] = Config(
                signature_version="s3v4",
                s3={
                    "addressing_style":
                        "virtual",
                },
            )

        return boto3.client(
            "s3",
            **kwargs,
        )

import mimetypes
from pathlib import Path

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.stored_media import (
    StoredMediaAsset,
)
from social_media_agent.services.media_store.path_utils import (
    normalize_storage_key,
)


class LocalMediaStore:

    PROVIDER_NAME = "local"

    def __init__(
        self,
        *,
        local_root: str | Path | None = None,
    ):
        self.local_root = Path(
            local_root
            if local_root is not None
            else settings.generated_assets_dir
        ).resolve()

    def verify_access(
        self,
    ) -> None:

        self.local_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self.local_root.is_dir():
            raise RuntimeError(
                "Local media store root is "
                "not a directory."
            )

    def store(
        self,
        storage_key: str,
    ) -> StoredMediaAsset:

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

        content_type = (
            mimetypes.guess_type(
                local_path.name
            )[0]
            or "application/octet-stream"
        )

        return StoredMediaAsset(
            source_storage_key=normalized,
            store_provider=self.PROVIDER_NAME,
            object_key=normalized,
            content_type=content_type,
            size_bytes=(
                local_path.stat().st_size
            ),
        )

    def create_download_url(
        self,
        media: StoredMediaAsset,
    ) -> str:

        raise RuntimeError(
            "LocalMediaStore does not expose "
            "a public download URL."
        )

    def resolve_path(
        self,
        media: StoredMediaAsset,
    ) -> Path:

        self._validate_media_provider(
            media
        )

        local_path = (
            self.local_root
            / Path(
                *media.object_key.split("/")
            )
        ).resolve()

        self._ensure_inside_root(
            local_path
        )

        return local_path

    def _validate_media_provider(
        self,
        media: StoredMediaAsset,
    ) -> None:

        if (
            media.store_provider
            != self.PROVIDER_NAME
        ):
            raise ValueError(
                "Stored media provider mismatch. "
                f"Expected={self.PROVIDER_NAME}, "
                f"actual={media.store_provider}."
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

from dataclasses import dataclass, field
from pathlib import PurePosixPath

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.publishing.instagram_preflight import (
    InstagramPublishingPreflight,
)


@dataclass(frozen=True)
class InstagramRunPreflightResult:
    run_id: str
    account_id: str
    username: str
    media_count: int | None
    media_provider: str
    image_providers: list[str] = field(
        default_factory=list
    )
    media_storage_keys: list[str] = field(
        default_factory=list
    )
    media_urls: list[str] = field(
        default_factory=list
    )
    storage_verified: bool = False

    @property
    def ready(self) -> bool:
        return bool(
            self.account_id
            and self.username
            and self.storage_verified
            and self.media_storage_keys
            and len(self.image_providers)
            == 1
            and len(self.media_urls)
            == len(self.media_storage_keys)
        )


class InstagramRunPreflightService:

    JPEG_EXTENSIONS = {
        ".jpg",
        ".jpeg",
    }

    def __init__(
        self,
        *,
        persistence,
        preflight: InstagramPublishingPreflight,
    ):
        self.persistence = persistence
        self.preflight = preflight

    def verify(
        self,
        run_id: str,
    ) -> InstagramRunPreflightResult:

        run = self.persistence.get_run(
            run_id
        )

        if run is None:
            raise ValueError(
                f"Content run not found: {run_id}"
            )

        if (
            run.status
            != RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ):
            raise ValueError(
                "Instagram preflight requires "
                "approved_for_publishing status. "
                f"Current status: {run.status}"
            )

        instagram_content = (
            self.persistence
            .get_latest_payload(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                platform="instagram",
            )
        )

        if instagram_content is None:
            raise ValueError(
                "This run has no Instagram "
                "platform content."
            )

        generated_payload = (
            self.persistence
            .get_latest_payload(
                run_id,
                ArtifactType.GENERATED_ASSETS,
            )
        )

        if generated_payload is None:
            raise ValueError(
                "This run has no generated "
                "media assets."
            )

        bundle = (
            GeneratedAssetBundle
            .model_validate(
                generated_payload
            )
        )

        instagram_assets = [
            asset
            for asset in bundle.images
            if asset.platform
            == "instagram"
        ]

        if not instagram_assets:
            raise ValueError(
                "This run has no generated "
                "Instagram images."
            )

        if (
            len(instagram_assets)
            > settings
            .instagram_max_carousel_items
        ):
            raise ValueError(
                "Instagram preflight found "
                f"{len(instagram_assets)} images, "
                "but the configured carousel limit "
                "is "
                f"{settings.instagram_max_carousel_items}."
            )

        invalid_media = [
            asset.storage_key
            for asset in instagram_assets
            if (
                PurePosixPath(
                    asset.storage_key.replace(
                        "\\",
                        "/",
                    )
                )
                .suffix
                .lower()
                not in self.JPEG_EXTENSIONS
            )
        ]

        if invalid_media:
            raise ValueError(
                "Instagram preflight requires "
                "JPEG media. Unsupported assets: "
                + ", ".join(
                    invalid_media
                )
            )

        image_providers = sorted(
            {
                asset.provider
                for asset
                in instagram_assets
            }
        )

        if len(image_providers) != 1:
            raise ValueError(
                "Instagram generated media must "
                "come from one consistent image "
                "provider. Found: "
                + ", ".join(
                    image_providers
                )
            )

        if (
            settings.publishing_mode
            .strip()
            .lower()
            == "live"
            and image_providers
            == [
                "development"
            ]
        ):
            raise ValueError(
                "Development placeholder images "
                "cannot be used for live Instagram "
                "publishing. Generate production "
                "images first."
            )

        resolver = (
            self.preflight
            .media_url_resolver
        )

        media_provider = str(
            getattr(
                resolver,
                "PROVIDER_NAME",
                resolver.__class__.__name__,
            )
        )

        verify_access = getattr(
            resolver,
            "verify_access",
            None,
        )

        if callable(
            verify_access
        ):
            verify_access()

        account_result = (
            self.preflight.verify()
        )

        storage_keys = [
            asset.storage_key
            for asset
            in instagram_assets
        ]

        media_urls = []

        for storage_key in storage_keys:

            media_url = (
                self.preflight.verify_media(
                    storage_key=storage_key
                )
            )

            media_urls.append(
                media_url
            )

        return InstagramRunPreflightResult(
            run_id=run_id,
            account_id=(
                account_result.account_id
            ),
            username=(
                account_result.username
            ),
            media_count=(
                account_result.media_count
            ),
            media_provider=(
                media_provider
            ),
            image_providers=(
                image_providers
            ),
            media_storage_keys=(
                storage_keys
            ),
            media_urls=media_urls,
            storage_verified=True,
        )

from dataclasses import dataclass, field

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
    media_storage_keys: list[str] = field(
        default_factory=list
    )
    media_urls: list[str] = field(
        default_factory=list
    )

    @property
    def ready(self) -> bool:
        return bool(
            self.account_id
            and self.username
            and self.media_storage_keys
            and len(self.media_urls)
            == len(self.media_storage_keys)
        )


class InstagramRunPreflightService:

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

        storage_keys = [
            asset.storage_key
            for asset in bundle.images
            if asset.platform
            == "instagram"
        ]

        if not storage_keys:
            raise ValueError(
                "This run has no generated "
                "Instagram images."
            )

        account_result = (
            self.preflight.verify()
        )

        media_urls = []

        for storage_key in storage_keys:

            media_result = (
                self.preflight.verify_media(
                    storage_key=storage_key
                )
            )

            media_urls.append(
                media_result
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
            media_storage_keys=(
                storage_keys
            ),
            media_urls=media_urls,
        )

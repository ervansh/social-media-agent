from pathlib import PurePosixPath

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.publication import (
    PublicationRequest,
    PublicationResult,
)
from social_media_agent.services.publishing.instagram_graph_client import (
    InstagramGraphClient,
)
from social_media_agent.services.publishing.media_url_resolver import (
    MediaUrlResolver,
)


class InstagramPublisher:

    JPEG_EXTENSIONS = {
        ".jpg",
        ".jpeg",
    }

    def __init__(
        self,
        *,
        client: InstagramGraphClient,
        media_url_resolver: MediaUrlResolver,
    ):
        self.client = client
        self.media_url_resolver = (
            media_url_resolver
        )

    def publish(
        self,
        request: PublicationRequest,
    ) -> PublicationResult:

        if request.platform != "instagram":
            raise ValueError(
                "InstagramPublisher only "
                "supports Instagram."
            )

        caption = str(
            request.payload.get(
                "caption",
                "",
            )
        ).strip()

        if not caption:
            raise ValueError(
                "Instagram publication payload "
                "does not contain a caption."
            )

        storage_keys = list(
            request.media_storage_keys
        )

        if not storage_keys:
            raise ValueError(
                "Instagram publishing requires "
                "at least one generated image."
            )

        max_items = (
            settings
            .instagram_max_carousel_items
        )

        if len(storage_keys) > max_items:
            raise ValueError(
                "Instagram publishing supports "
                f"at most {max_items} carousel "
                "images per publication."
            )

        self._validate_image_keys(
            storage_keys
        )

        media_urls = [
            self.media_url_resolver.resolve(
                storage_key
            )
            for storage_key
            in storage_keys
        ]

        if len(media_urls) == 1:

            container_id = (
                self.client
                .create_image_container(
                    image_url=(
                        media_urls[0]
                    ),
                    caption=caption,
                )
            )

            media_id = (
                self.client
                .publish_container(
                    container_id
                )
            )

            return PublicationResult(
                platform="instagram",
                status="published",
                message=(
                    "Instagram image "
                    "published successfully."
                ),
                external_id=media_id,
                response_payload={
                    "publication_type":
                        "image",
                    "container_id":
                        container_id,
                },
            )

        child_container_ids = []

        for media_url in media_urls:

            child_container_ids.append(
                self.client
                .create_image_container(
                    image_url=media_url,
                    is_carousel_item=True,
                )
            )

        parent_container_id = (
            self.client
            .create_carousel_container(
                child_container_ids=(
                    child_container_ids
                ),
                caption=caption,
            )
        )

        media_id = (
            self.client
            .publish_container(
                parent_container_id
            )
        )

        return PublicationResult(
            platform="instagram",
            status="published",
            message=(
                "Instagram carousel "
                "published successfully."
            ),
            external_id=media_id,
            response_payload={
                "publication_type":
                    "carousel",
                "container_id":
                    parent_container_id,
                "child_container_ids":
                    child_container_ids,
            },
        )

    def _validate_image_keys(
        self,
        storage_keys: list[str],
    ) -> None:

        invalid = []

        for storage_key in storage_keys:

            normalized = (
                storage_key
                .replace("\\", "/")
            )

            extension = (
                PurePosixPath(
                    normalized
                )
                .suffix
                .lower()
            )

            if (
                extension
                not in self.JPEG_EXTENSIONS
            ):
                invalid.append(
                    storage_key
                )

        if invalid:
            raise ValueError(
                "Instagram feed publishing "
                "requires JPEG media. "
                "Generate Instagram assets as "
                "JPG/JPEG before live publishing. "
                "Unsupported assets: "
                + ", ".join(invalid)
            )

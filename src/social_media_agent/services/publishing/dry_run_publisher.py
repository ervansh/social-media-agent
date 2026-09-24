from social_media_agent.models.publication import (
    PublicationRequest,
    PublicationResult,
)


class DryRunPublisher:

    def publish(
        self,
        request: PublicationRequest,
    ) -> PublicationResult:

        return PublicationResult(
            platform=request.platform,
            status="dry_run",
            message=(
                f"Dry-run completed for "
                f"{request.platform}. "
                "Nothing was published."
            ),
            response_payload={
                "payload": request.payload,
                "media_storage_keys":
                    request.media_storage_keys,
            },
        )
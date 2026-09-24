from pathlib import Path

from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)
from social_media_agent.models.publication import (
    PublicationBatch,
    PublicationRequest,
    PublicationResult,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)


class PublishingService:

    def __init__(
        self,
        persistence,
        publishers: dict,
    ):
        self.persistence = persistence
        self.publishers = publishers

    def publish(
        self,
        run_id: str,
    ) -> PublicationBatch:

        run = self.persistence.get_run(
            run_id
        )

        if run is None:
            raise ValueError(
                f"Content run not found: {run_id}"
            )

        if (
            run.status
            == RunStatus.PUBLISHED.value
        ):
            previous = (
                self._load_latest_batch(
                    run_id
                )
            )

            if previous is not None:
                return previous

        if (
            run.status
            != RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ):
            raise ValueError(
                "Publishing requires run status "
                "approved_for_publishing. "
                f"Current status: {run.status}"
            )

        requests = self._build_requests(
            run_id
        )

        previously_published = (
            self._load_published_results(
                run_id
            )
        )

        results: list[
            PublicationResult
        ] = []

        for request in requests:

            previous_result = (
                previously_published.get(
                    request.platform
                )
            )

            if previous_result is not None:

                results.append(
                    PublicationResult(
                        platform=(
                            previous_result
                            .platform
                        ),
                        status="published",
                        message=(
                            "Already published; "
                            "existing publication "
                            "result reused."
                        ),
                        external_id=(
                            previous_result
                            .external_id
                        ),
                        response_payload={
                            **(
                                previous_result
                                .response_payload
                            ),
                            "idempotent_reuse":
                                True,
                        },
                    )
                )

                continue

            readiness_error = (
                self._check_readiness(
                    request
                )
            )

            if readiness_error:

                results.append(
                    PublicationResult(
                        platform=request.platform,
                        status="blocked",
                        message=readiness_error,
                    )
                )

                continue

            publisher = (
                self.publishers.get(
                    request.platform
                )
            )

            if publisher is None:

                results.append(
                    PublicationResult(
                        platform=request.platform,
                        status="blocked",
                        message=(
                            "No publisher configured "
                            "for this platform."
                        ),
                    )
                )

                continue

            try:

                result = publisher.publish(
                    request
                )

                results.append(
                    result
                )

            except Exception as exc:

                results.append(
                    PublicationResult(
                        platform=request.platform,
                        status="failed",
                        message=str(exc),
                    )
                )

        batch = PublicationBatch(
            results=results
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.PUBLICATION_RESULT,
            batch,
        )

        if (
            results
            and all(
                result.status
                in {
                    "published",
                    "dry_run",
                }
                for result in results
            )
            and any(
                result.status
                == "published"
                for result in results
            )
        ):
            self.persistence.update_status(
                run_id,
                RunStatus.PUBLISHED.value,
            )

        return batch

    def _check_readiness(
        self,
        request: PublicationRequest,
    ) -> str | None:

        if request.platform == "youtube":

            if not self._has_video(
                request.media_storage_keys
            ):
                return (
                    "YouTube publishing requires "
                    "a final video file."
                )

        if request.platform == "instagram":

            if not request.media_storage_keys:
                return (
                    "Instagram publishing requires "
                    "generated media."
                )

        return None

    def _build_requests(
        self,
        run_id: str,
    ) -> list[PublicationRequest]:

        requests: list[
            PublicationRequest
        ] = []

        media_by_platform = (
            self._load_media(
                run_id
            )
        )

        for platform in (
            "youtube",
            "instagram",
            "x",
        ):

            payload = (
                self.persistence
                .get_latest_payload(
                    run_id,
                    ArtifactType.PLATFORM_CONTENT,
                    platform=platform,
                )
            )

            if payload is None:
                continue

            requests.append(
                PublicationRequest(
                    run_id=run_id,
                    platform=platform,
                    payload=(
                        self._build_platform_payload(
                            platform,
                            payload,
                        )
                    ),
                    media_storage_keys=(
                        media_by_platform.get(
                            platform,
                            [],
                        )
                    ),
                )
            )

        return requests

    def _load_media(
        self,
        run_id: str,
    ) -> dict[str, list[str]]:

        payload = (
            self.persistence
            .get_latest_payload(
                run_id,
                ArtifactType.GENERATED_ASSETS,
            )
        )

        if payload is None:
            return {}

        bundle = (
            GeneratedAssetBundle
            .model_validate(
                payload
            )
        )

        media: dict[
            str,
            list[str],
        ] = {}

        for asset in bundle.images:

            media.setdefault(
                asset.platform,
                [],
            ).append(
                asset.storage_key
            )

        return media

    def _load_latest_batch(
        self,
        run_id: str,
    ) -> PublicationBatch | None:

        payload = (
            self.persistence
            .get_latest_payload(
                run_id,
                ArtifactType.PUBLICATION_RESULT,
            )
        )

        if payload is None:
            return None

        return PublicationBatch.model_validate(
            payload
        )

    def _load_published_results(
        self,
        run_id: str,
    ) -> dict[str, PublicationResult]:

        batch = self._load_latest_batch(
            run_id
        )

        if batch is None:
            return {}

        return {
            result.platform: result
            for result in batch.results
            if result.status == "published"
        }

    @staticmethod
    def _build_platform_payload(
        platform: str,
        payload: dict,
    ) -> dict:

        if platform == "x":

            return {
                "text": payload[
                    "single_post"
                ]
            }

        if platform == "youtube":

            return {
                "title": payload[
                    "title"
                ],
                "description": payload[
                    "description"
                ],
            }

        if platform == "instagram":

            return {
                "caption": payload[
                    "caption"
                ],
            }

        raise ValueError(
            f"Unsupported platform: "
            f"{platform}"
        )

    @staticmethod
    def _has_video(
        storage_keys: list[str],
    ) -> bool:

        video_extensions = {
            ".mp4",
            ".mov",
            ".m4v",
            ".webm",
        }

        return any(
            Path(key).suffix.lower()
            in video_extensions
            for key in storage_keys
        )

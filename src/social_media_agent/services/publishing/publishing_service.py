from pathlib import Path

from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)
from social_media_agent.models.publication import (
    PublicationBatch,
    PublicationRequest,
    PublicationResult,
)
from social_media_agent.models.publication_plan import (
    ArtifactVersionRef,
    PublicationPlan,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.publishing.publication_plan_service import (
    PublicationPlanService,
)


class PublishingService:

    def __init__(
        self,
        persistence,
        publishers: dict,
    ):
        self.persistence = persistence
        self.publishers = publishers
        self.plan_service = (
            PublicationPlanService(
                persistence=persistence
            )
        )

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

        plan = (
            self.plan_service
            .load_latest(
                run_id
            )
        )

        if plan is None:
            raise ValueError(
                "Publishing requires a "
                "version-locked publication plan. "
                "Approve the current content "
                "before publishing."
            )

        self.plan_service.assert_current(
            run_id=run_id,
            plan=plan,
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

            if (
                previous is not None
                and previous
                .publication_plan_id
                == plan.plan_id
            ):
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
            run_id=run_id,
            plan=plan,
        )

        previously_published = (
            self._load_published_results(
                run_id=run_id,
                publication_plan_id=(
                    plan.plan_id
                ),
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
                            "Already published for "
                            "this publication plan; "
                            "existing result reused."
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
                            "publication_plan_id":
                                plan.plan_id,
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
            publication_plan_id=(
                plan.plan_id
            ),
            results=results,
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
        *,
        run_id: str,
        plan: PublicationPlan,
    ) -> list[PublicationRequest]:

        requests: list[
            PublicationRequest
        ] = []

        generated_ref = plan.get_ref(
            artifact_type=(
                ArtifactType
                .GENERATED_ASSETS
                .value
            )
        )

        media_by_platform = (
            self._load_media(
                run_id=run_id,
                generated_ref=(
                    generated_ref
                ),
            )
        )

        for platform in plan.platforms:

            content_ref = plan.get_ref(
                artifact_type=(
                    ArtifactType
                    .PLATFORM_CONTENT
                    .value
                ),
                platform=platform,
            )

            if content_ref is None:
                raise ValueError(
                    "Publication plan is missing "
                    "platform content reference "
                    f"for {platform}."
                )

            payload = (
                self.persistence
                .get_payload_at_version(
                    run_id=run_id,
                    artifact_type=(
                        ArtifactType
                        .PLATFORM_CONTENT
                    ),
                    platform=platform,
                    version=(
                        content_ref.version
                    ),
                )
            )

            if payload is None:
                raise ValueError(
                    "Frozen platform content "
                    "artifact could not be loaded. "
                    f"platform={platform}, "
                    f"version={content_ref.version}"
                )

            requests.append(
                PublicationRequest(
                    run_id=run_id,
                    platform=platform,
                    publication_plan_id=(
                        plan.plan_id
                    ),
                    content_artifact_version=(
                        content_ref.version
                    ),
                    generated_assets_version=(
                        generated_ref.version
                        if generated_ref
                        is not None
                        else None
                    ),
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
        *,
        run_id: str,
        generated_ref: ArtifactVersionRef | None,
    ) -> dict[str, list[str]]:

        if generated_ref is None:
            return {}

        payload = (
            self.persistence
            .get_payload_at_version(
                run_id=run_id,
                artifact_type=(
                    ArtifactType
                    .GENERATED_ASSETS
                ),
                version=(
                    generated_ref.version
                ),
            )
        )

        if payload is None:
            raise ValueError(
                "Frozen generated-assets "
                "artifact could not be loaded. "
                f"version={generated_ref.version}"
            )

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
        *,
        run_id: str,
        publication_plan_id: str,
    ) -> dict[str, PublicationResult]:

        batch = self._load_latest_batch(
            run_id
        )

        if (
            batch is None
            or batch.publication_plan_id
            != publication_plan_id
        ):
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

from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
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


class PublicationPlanService:

    SNAPSHOT_TYPES = {
        ArtifactType.RESEARCH.value,
        ArtifactType.SELECTED_IDEA.value,
        ArtifactType.STRATEGY.value,
        ArtifactType.MASTER_CONTENT.value,
        ArtifactType.GROUNDING_REPORT.value,
        ArtifactType.PLATFORM_CONTENT.value,
        ArtifactType.PLATFORM_GROUNDING_REPORT.value,
        ArtifactType.QUALITY_REPORT.value,
        ArtifactType.CREATIVE_ASSETS.value,
        ArtifactType.GENERATED_ASSETS.value,
    }

    def __init__(
        self,
        *,
        persistence,
    ):
        self.persistence = persistence

    def create_for_run(
        self,
        run_id: str,
    ) -> PublicationPlan:

        run = self.persistence.get_run(
            run_id
        )

        if run is None:
            raise ValueError(
                f"Content run not found: {run_id}"
            )

        if run.status not in {
            RunStatus
            .READY_FOR_HUMAN_REVIEW
            .value,
            RunStatus
            .REQUIRES_REVIEW
            .value,
        }:
            raise ValueError(
                "Publication plan can only be "
                "created from content awaiting "
                "human review. "
                f"Current status: {run.status}"
            )

        artifacts = (
            self.persistence
            .get_latest_artifacts(
                run_id
            )
        )

        by_key = {
            (
                artifact.artifact_type,
                artifact.platform,
            ): artifact
            for artifact in artifacts
        }

        self._require_passed_report(
            by_key,
            ArtifactType
            .GROUNDING_REPORT
            .value,
        )

        self._require_passed_report(
            by_key,
            ArtifactType
            .PLATFORM_GROUNDING_REPORT
            .value,
        )

        self._require_passed_report(
            by_key,
            ArtifactType
            .QUALITY_REPORT
            .value,
        )

        platform_artifacts = sorted(
            [
                artifact
                for artifact
                in artifacts
                if (
                    artifact.artifact_type
                    == ArtifactType
                    .PLATFORM_CONTENT
                    .value
                    and artifact.platform
                )
            ],
            key=lambda artifact: (
                artifact.platform
            ),
        )

        if not platform_artifacts:
            raise ValueError(
                "Cannot create publication plan "
                "without platform content."
            )

        platforms = [
            str(
                artifact.platform
            )
            for artifact
            in platform_artifacts
        ]

        generated_artifact = (
            by_key.get(
                (
                    ArtifactType
                    .GENERATED_ASSETS
                    .value,
                    None,
                )
            )
        )

        if (
            "instagram"
            in platforms
        ):
            if generated_artifact is None:
                raise ValueError(
                    "Instagram publication plan "
                    "requires generated media."
                )

            bundle = (
                GeneratedAssetBundle
                .model_validate(
                    generated_artifact
                    .payload
                )
            )

            if not any(
                asset.platform
                == "instagram"
                for asset
                in bundle.images
            ):
                raise ValueError(
                    "Instagram publication plan "
                    "requires generated Instagram "
                    "media."
                )

        snapshot_artifacts = [
            artifact
            for artifact
            in artifacts
            if artifact.artifact_type
            in self.SNAPSHOT_TYPES
        ]

        refs = [
            ArtifactVersionRef(
                artifact_id=artifact.id,
                artifact_type=(
                    artifact.artifact_type
                ),
                platform=artifact.platform,
                version=artifact.version,
            )
            for artifact
            in sorted(
                snapshot_artifacts,
                key=lambda artifact: (
                    artifact.artifact_type,
                    artifact.platform
                    or "",
                ),
            )
        ]

        plan = PublicationPlan(
            run_id=run_id,
            platforms=platforms,
            artifact_refs=refs,
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.PUBLICATION_PLAN,
            plan,
        )

        return plan

    def load_latest(
        self,
        run_id: str,
    ) -> PublicationPlan | None:

        payload = (
            self.persistence
            .get_latest_payload(
                run_id,
                ArtifactType.PUBLICATION_PLAN,
            )
        )

        if payload is None:
            return None

        return (
            PublicationPlan
            .model_validate(
                payload
            )
        )

    def assert_current(
        self,
        *,
        run_id: str,
        plan: PublicationPlan,
    ) -> None:

        latest = {
            (
                artifact.artifact_type,
                artifact.platform,
            ): artifact
            for artifact
            in self.persistence
            .get_latest_artifacts(
                run_id
            )
        }

        stale_refs = []

        for ref in plan.artifact_refs:

            current = latest.get(
                (
                    ref.artifact_type,
                    ref.platform,
                )
            )

            if (
                current is None
                or current.id
                != ref.artifact_id
                or current.version
                != ref.version
            ):
                stale_refs.append(
                    (
                        ref.artifact_type,
                        ref.platform,
                        ref.version,
                    )
                )

        if stale_refs:

            self.persistence.update_status(
                run_id,
                RunStatus
                .REQUIRES_REVIEW
                .value,
            )

            raise ValueError(
                "Publication plan is stale "
                "because reviewed artifacts "
                "changed after approval. "
                "Human review is required again."
            )

    @staticmethod
    def _require_passed_report(
        by_key: dict,
        artifact_type: str,
    ) -> None:

        artifact = by_key.get(
            (
                artifact_type,
                None,
            )
        )

        if artifact is None:
            raise ValueError(
                "Publication plan requires "
                f"{artifact_type}."
            )

        if not artifact.payload.get(
            "passed",
            False,
        ):
            raise ValueError(
                "Publication plan requires a "
                f"passing {artifact_type}."
            )

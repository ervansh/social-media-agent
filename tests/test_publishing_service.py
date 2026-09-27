import pytest

from social_media_agent.models.publication import (
    PublicationBatch,
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
from social_media_agent.services.publishing.publishing_service import (
    PublishingService,
)


class FakeRun:

    def __init__(
        self,
        status,
    ):
        self.status = status


class FakeArtifact:

    def __init__(
        self,
        *,
        artifact_id,
        artifact_type,
        platform,
        version,
        payload,
    ):
        self.id = artifact_id
        self.artifact_type = artifact_type
        self.platform = platform
        self.version = version
        self.payload = payload


class FakePersistence:

    def __init__(
        self,
        *,
        status,
        platform_payloads=None,
        publication_batch=None,
        include_plan=True,
    ):
        self.run = FakeRun(
            status
        )

        self.platform_payloads = (
            platform_payloads
            or {}
        )

        self.publication_batch = (
            publication_batch
        )

        self.saved_batches = []
        self.status_updates = []

        self.artifacts = []

        refs = []

        for platform, payload in (
            self.platform_payloads
            .items()
        ):
            artifact = FakeArtifact(
                artifact_id=(
                    f"{platform}-content-v1"
                ),
                artifact_type=(
                    ArtifactType
                    .PLATFORM_CONTENT
                    .value
                ),
                platform=platform,
                version=1,
                payload=payload,
            )

            self.artifacts.append(
                artifact
            )

            refs.append(
                ArtifactVersionRef(
                    artifact_id=artifact.id,
                    artifact_type=(
                        artifact.artifact_type
                    ),
                    platform=platform,
                    version=1,
                )
            )

        self.plan = (
            PublicationPlan(
                plan_id="plan-1",
                run_id="run-1",
                platforms=sorted(
                    self.platform_payloads
                ),
                artifact_refs=refs,
            )
            if include_plan
            and refs
            else None
        )

    def get_run(
        self,
        run_id,
    ):
        return self.run

    def get_latest_artifacts(
        self,
        run_id,
    ):
        return list(
            self.artifacts
        )

    def get_payload_at_version(
        self,
        run_id,
        artifact_type,
        version,
        platform=None,
    ):
        artifact_name = (
            artifact_type.value
            if isinstance(
                artifact_type,
                ArtifactType,
            )
            else artifact_type
        )

        for artifact in self.artifacts:

            if (
                artifact.artifact_type
                == artifact_name
                and artifact.platform
                == platform
                and artifact.version
                == version
            ):
                return artifact.payload

        return None

    def get_latest_payload(
        self,
        run_id,
        artifact_type,
        platform=None,
    ):

        if (
            artifact_type
            == ArtifactType
            .PUBLICATION_PLAN
        ):
            if self.plan is None:
                return None

            return self.plan.model_dump(
                mode="json"
            )

        if (
            artifact_type
            == ArtifactType
            .PUBLICATION_RESULT
        ):
            if (
                self.publication_batch
                is None
            ):
                return None

            return (
                self.publication_batch
                .model_dump(
                    mode="json"
                )
            )

        return None

    def save_model(
        self,
        run_id,
        artifact_type,
        model,
        platform=None,
    ):
        self.saved_batches.append(
            model
        )

        if (
            artifact_type
            == ArtifactType
            .PUBLICATION_RESULT
        ):
            self.publication_batch = (
                model
            )

    def update_status(
        self,
        run_id,
        status,
    ):
        self.run.status = status
        self.status_updates.append(
            status
        )


class FakePublisher:

    def __init__(
        self,
        external_id,
    ):
        self.external_id = external_id
        self.calls = 0
        self.requests = []

    def publish(
        self,
        request,
    ):
        self.calls += 1
        self.requests.append(
            request
        )

        return PublicationResult(
            platform=request.platform,
            status="published",
            message="Published",
            external_id=(
                self.external_id
            ),
        )


def test_publish_requires_approval():

    persistence = FakePersistence(
        status=(
            RunStatus
            .READY_FOR_HUMAN_REVIEW
            .value
        ),
        platform_payloads={
            "x": {
                "single_post":
                    "Hello"
            }
        },
    )

    service = PublishingService(
        persistence=persistence,
        publishers={},
    )

    with pytest.raises(
        ValueError,
        match="approved_for_publishing",
    ):
        service.publish(
            "run-1"
        )


def test_publish_requires_version_locked_plan():

    persistence = FakePersistence(
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
        platform_payloads={
            "x": {
                "single_post":
                    "Hello"
            }
        },
        include_plan=False,
    )

    service = PublishingService(
        persistence=persistence,
        publishers={},
    )

    with pytest.raises(
        ValueError,
        match="version-locked publication plan",
    ):
        service.publish(
            "run-1"
        )


def test_successful_publication_uses_frozen_version_and_marks_published():

    persistence = FakePersistence(
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
        platform_payloads={
            "x": {
                "single_post":
                    "Approved content"
            }
        },
    )

    x_publisher = FakePublisher(
        "x-123"
    )

    service = PublishingService(
        persistence=persistence,
        publishers={
            "x": x_publisher
        },
    )

    batch = service.publish(
        "run-1"
    )

    assert (
        batch.publication_plan_id
        == "plan-1"
    )

    assert (
        batch.results[0].status
        == "published"
    )

    request = (
        x_publisher.requests[0]
    )

    assert (
        request.publication_plan_id
        == "plan-1"
    )

    assert (
        request.content_artifact_version
        == 1
    )

    assert request.payload == {
        "text":
            "Approved content"
    }

    assert (
        persistence.run.status
        == RunStatus.PUBLISHED.value
    )


def test_previous_success_is_not_published_twice_for_same_plan():

    previous = PublicationBatch(
        publication_plan_id="plan-1",
        results=[
            PublicationResult(
                platform="x",
                status="published",
                message="Published",
                external_id="x-123",
            )
        ],
    )

    persistence = FakePersistence(
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
        platform_payloads={
            "x": {
                "single_post":
                    "Hello"
            }
        },
        publication_batch=previous,
    )

    x_publisher = FakePublisher(
        "x-new"
    )

    service = PublishingService(
        persistence=persistence,
        publishers={
            "x": x_publisher
        },
    )

    batch = service.publish(
        "run-1"
    )

    assert x_publisher.calls == 0

    assert (
        batch.results[0].external_id
        == "x-123"
    )

    assert (
        batch.results[0]
        .response_payload[
            "idempotent_reuse"
        ]
        is True
    )


def test_missing_live_publisher_blocks_completion():

    persistence = FakePersistence(
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
        platform_payloads={
            "youtube": {
                "title": "Title",
                "description": "Description",
            }
        },
    )

    service = PublishingService(
        persistence=persistence,
        publishers={},
    )

    batch = service.publish(
        "run-1"
    )

    assert (
        batch.results[0].status
        == "blocked"
    )

    assert (
        persistence.run.status
        == RunStatus
        .APPROVED_FOR_PUBLISHING
        .value
    )


def test_stale_plan_requires_human_review():

    persistence = FakePersistence(
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
        platform_payloads={
            "x": {
                "single_post":
                    "Approved content"
            }
        },
    )

    persistence.artifacts[0].version = 2

    service = PublishingService(
        persistence=persistence,
        publishers={
            "x":
                FakePublisher(
                    "x-123"
                )
        },
    )

    with pytest.raises(
        ValueError,
        match="Publication plan is stale",
    ):
        service.publish(
            "run-1"
        )

    assert (
        persistence.run.status
        == RunStatus
        .REQUIRES_REVIEW
        .value
    )

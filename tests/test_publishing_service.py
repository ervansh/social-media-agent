import pytest

from social_media_agent.models.publication import (
    PublicationBatch,
    PublicationResult,
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


class FakePersistence:

    def __init__(
        self,
        *,
        status,
        platform_payloads=None,
        publication_batch=None,
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

    def get_run(
        self,
        run_id,
    ):
        return self.run

    def get_latest_payload(
        self,
        run_id,
        artifact_type,
        platform=None,
    ):

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

        if (
            artifact_type
            == ArtifactType
            .GENERATED_ASSETS
        ):
            return None

        if (
            artifact_type
            == ArtifactType
            .PLATFORM_CONTENT
        ):
            return (
                self.platform_payloads
                .get(platform)
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

    def publish(
        self,
        request,
    ):
        self.calls += 1

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


def test_successful_publication_marks_run_published():

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
        batch.results[0].status
        == "published"
    )

    assert (
        persistence.run.status
        == RunStatus.PUBLISHED.value
    )


def test_previous_success_is_not_published_twice():

    previous = PublicationBatch(
        results=[
            PublicationResult(
                platform="x",
                status="published",
                message="Published",
                external_id="x-123",
            )
        ]
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

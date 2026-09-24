from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.publishing.instagram_run_preflight import (
    InstagramRunPreflightService,
)


class FakeRun:

    def __init__(
        self,
        status,
    ):
        self.status = status


class FakePersistence:

    def __init__(self):
        self.run = FakeRun(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        )

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
            .PLATFORM_CONTENT
            and platform
            == "instagram"
        ):
            return {
                "caption":
                    "Test caption"
            }

        if (
            artifact_type
            == ArtifactType
            .GENERATED_ASSETS
        ):
            return {
                "images": [
                    {
                        "platform":
                            "instagram",
                        "asset_type":
                            "carousel_slide_1",
                        "storage_key":
                            "run-1/1.jpg",
                        "provider":
                            "fake",
                        "model":
                            "fake",
                        "requested_width":
                            1080,
                        "requested_height":
                            1350,
                        "generated_width":
                            1080,
                        "generated_height":
                            1350,
                        "prompt":
                            "one",
                    },
                    {
                        "platform":
                            "instagram",
                        "asset_type":
                            "carousel_slide_2",
                        "storage_key":
                            "run-1/2.jpg",
                        "provider":
                            "fake",
                        "model":
                            "fake",
                        "requested_width":
                            1080,
                        "requested_height":
                            1350,
                        "generated_width":
                            1080,
                        "generated_height":
                            1350,
                        "prompt":
                            "two",
                    },
                ]
            }

        return None


class FakeAccountResult:

    account_id = "ig-123"
    username = "qa_account"
    media_count = 7


class FakePreflight:

    def __init__(self):
        self.verified = []

    def verify(self):
        return FakeAccountResult()

    def verify_media(
        self,
        *,
        storage_key,
    ):
        self.verified.append(
            storage_key
        )

        return (
            "https://cdn.example.com/"
            f"{storage_key}"
        )


def test_run_preflight_verifies_all_instagram_media():

    persistence = FakePersistence()
    preflight = FakePreflight()

    service = (
        InstagramRunPreflightService(
            persistence=persistence,
            preflight=preflight,
        )
    )

    result = service.verify(
        "run-1"
    )

    assert result.ready is True
    assert result.username == "qa_account"

    assert result.media_storage_keys == [
        "run-1/1.jpg",
        "run-1/2.jpg",
    ]

    assert result.media_urls == [
        (
            "https://cdn.example.com/"
            "run-1/1.jpg"
        ),
        (
            "https://cdn.example.com/"
            "run-1/2.jpg"
        ),
    ]

    assert preflight.verified == [
        "run-1/1.jpg",
        "run-1/2.jpg",
    ]

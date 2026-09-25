import pytest

from social_media_agent.config.settings import (
    settings,
)
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

    def __init__(
        self,
        *,
        providers=None,
        extensions=None,
    ):
        self.run = FakeRun(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        )

        providers = (
            providers
            or [
                "openai",
                "openai",
            ]
        )

        extensions = (
            extensions
            or [
                ".jpg",
                ".jpeg",
            ]
        )

        self.images = []

        for index, (
            provider,
            extension,
        ) in enumerate(
            zip(
                providers,
                extensions,
                strict=True,
            ),
            start=1,
        ):
            self.images.append(
                {
                    "platform":
                        "instagram",
                    "asset_type":
                        (
                            "carousel_slide_"
                            f"{index}"
                        ),
                    "storage_key":
                        (
                            f"run-1/{index}"
                            f"{extension}"
                        ),
                    "provider":
                        provider,
                    "model":
                        "model",
                    "requested_width":
                        1080,
                    "requested_height":
                        1350,
                    "generated_width":
                        1088,
                    "generated_height":
                        1360,
                    "prompt":
                        f"prompt-{index}",
                }
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
                "images":
                    self.images
            }

        return None


class FakeAccountResult:

    account_id = "ig-123"
    username = "qa_account"
    media_count = 7


class FakeResolver:

    PROVIDER_NAME = "s3"

    def __init__(self):
        self.access_checks = 0

    def verify_access(self):
        self.access_checks += 1


class FakePreflight:

    def __init__(self):
        self.verified = []
        self.media_url_resolver = (
            FakeResolver()
        )

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


def test_run_preflight_verifies_all_instagram_media(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "publishing_mode",
        "dry_run",
    )

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
    assert result.media_provider == "s3"
    assert result.image_providers == [
        "openai"
    ]
    assert (
        result.storage_verified
        is True
    )

    assert result.media_storage_keys == [
        "run-1/1.jpg",
        "run-1/2.jpeg",
    ]

    assert result.media_urls == [
        (
            "https://cdn.example.com/"
            "run-1/1.jpg"
        ),
        (
            "https://cdn.example.com/"
            "run-1/2.jpeg"
        ),
    ]

    assert preflight.verified == [
        "run-1/1.jpg",
        "run-1/2.jpeg",
    ]

    assert (
        preflight
        .media_url_resolver
        .access_checks
        == 1
    )


def test_live_preflight_rejects_development_images(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "publishing_mode",
        "live",
    )

    service = (
        InstagramRunPreflightService(
            persistence=FakePersistence(
                providers=[
                    "development",
                    "development",
                ]
            ),
            preflight=FakePreflight(),
        )
    )

    with pytest.raises(
        ValueError,
        match="Development placeholder",
    ):
        service.verify(
            "run-1"
        )


def test_preflight_rejects_non_jpeg_media(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "publishing_mode",
        "dry_run",
    )

    service = (
        InstagramRunPreflightService(
            persistence=FakePersistence(
                extensions=[
                    ".jpg",
                    ".png",
                ]
            ),
            preflight=FakePreflight(),
        )
    )

    with pytest.raises(
        ValueError,
        match="requires JPEG media",
    ):
        service.verify(
            "run-1"
        )


def test_preflight_rejects_mixed_image_providers(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "publishing_mode",
        "dry_run",
    )

    service = (
        InstagramRunPreflightService(
            persistence=FakePersistence(
                providers=[
                    "development",
                    "openai",
                ]
            ),
            preflight=FakePreflight(),
        )
    )

    with pytest.raises(
        ValueError,
        match="one consistent image provider",
    ):
        service.verify(
            "run-1"
        )

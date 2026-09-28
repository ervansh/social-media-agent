import hashlib
import json
import mimetypes
from pathlib import Path

import pytest

from social_media_agent.models.publication_plan import (
    ArtifactVersionRef,
    PublicationPlan,
)
from social_media_agent.models.stored_media import (
    StoredMediaAsset,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.publishing.manual_publish_package_service import (
    ManualPublishPackageService,
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


class RecordingMediaStore:

    PROVIDER_NAME = "recording"

    def __init__(
        self,
        root: Path,
    ):
        self.root = root
        self.calls = []
        self.verified = False

    def verify_access(self):
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.verified = True

    def store(
        self,
        storage_key: str,
    ) -> StoredMediaAsset:

        path = (
            self.root
            / Path(
                *storage_key.split("/")
            )
        )

        assert path.is_file()

        self.calls.append(
            storage_key
        )

        return StoredMediaAsset(
            source_storage_key=storage_key,
            store_provider=self.PROVIDER_NAME,
            object_key=(
                "stored/"
                f"{storage_key}"
            ),
            content_type=(
                mimetypes.guess_type(
                    path.name
                )[0]
                or "application/octet-stream"
            ),
            size_bytes=(
                path.stat().st_size
            ),
        )

    def create_download_url(
        self,
        media,
    ):
        return (
            "https://example.com/"
            f"{media.object_key}"
        )


class FakePersistence:

    def __init__(
        self,
        *,
        plan,
        artifacts,
        payloads,
        status=(
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value
        ),
    ):
        self.run = FakeRun(
            status
        )
        self.plan = plan
        self.artifacts = artifacts
        self.payloads = payloads
        self.saved = []
        self.status_updates = []
        self.version_reads = []

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
            .PUBLICATION_PLAN
        ):
            return self.plan.model_dump(
                mode="json"
            )

        return None

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
        name = (
            artifact_type.value
            if isinstance(
                artifact_type,
                ArtifactType,
            )
            else artifact_type
        )

        key = (
            name,
            platform,
            version,
        )

        self.version_reads.append(
            key
        )

        return self.payloads.get(
            key
        )

    def save_model(
        self,
        run_id,
        artifact_type,
        model,
        platform=None,
    ):
        self.saved.append(
            (
                artifact_type,
                model,
            )
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


def build_fixture(
    tmp_path,
):

    generated_root = (
        tmp_path
        / "generated"
    )

    package_root = (
        tmp_path
        / "packages"
    )

    (
        generated_root
        / "run-1"
    ).mkdir(
        parents=True
    )

    (
        generated_root
        / "run-1"
        / "ig.jpeg"
    ).write_bytes(
        b"instagram-image"
    )

    (
        generated_root
        / "run-1"
        / "x.jpeg"
    ).write_bytes(
        b"x-image"
    )

    (
        generated_root
        / "run-1"
        / "reel.mp4"
    ).write_bytes(
        b"reel-video"
    )

    instagram_payload = {
        "reel_hook":
            "Instagram hook",
        "reel_script":
            "Instagram reel script",
        "caption":
            "Approved Instagram caption",
        "carousel_slides": [
            {
                "position": 1,
                "headline":
                    "Slide one",
                "body":
                    "Grounded body",
            }
        ],
        "hashtags": [
            "#qa",
            "#ai",
        ],
        "call_to_action":
            "Review the points.",
    }

    x_payload = {
        "single_post":
            "Approved X post",
        "thread": [
            "Thread one",
            "Thread two",
        ],
        "call_to_action":
            "Review the points.",
    }

    creative_payload = {
        "images": [],
        "storyboards": [
            {
                "platform":
                    "instagram",
                "asset_type":
                    "reel_storyboard",
                "scenes": [
                    {
                        "scene_number": 1,
                        "narration":
                            "Narration",
                        "visual_direction":
                            "Visual",
                        "on_screen_text":
                            "Text",
                    }
                ],
            }
        ],
    }

    generated_payload = {
        "images": [
            {
                "platform":
                    "instagram",
                "asset_type":
                    "carousel_slide_1",
                "storage_key":
                    "run-1/ig.jpeg",
                "provider":
                    "development",
                "model":
                    "deterministic-placeholder-v1",
                "requested_width":
                    1080,
                "requested_height":
                    1350,
                "generated_width":
                    1080,
                "generated_height":
                    1350,
                "prompt":
                    "Instagram prompt",
            },
            {
                "platform":
                    "x",
                "asset_type":
                    "supporting_visual",
                "storage_key":
                    "run-1/x.jpeg",
                "provider":
                    "development",
                "model":
                    "deterministic-placeholder-v1",
                "requested_width":
                    1600,
                "requested_height":
                    900,
                "generated_width":
                    1600,
                "generated_height":
                    900,
                "prompt":
                    "X prompt",
            },
        ],
        "videos": [
            {
                "platform":
                    "instagram",
                "asset_type":
                    "reel_video",
                "storyboard_asset_type":
                    "reel_storyboard",
                "storage_key":
                    "run-1/reel.mp4",
                "provider":
                    "ffmpeg",
                "model":
                    "deterministic-still-motion-v1",
                "width":
                    1080,
                "height":
                    1920,
                "fps":
                    30,
                "duration_seconds":
                    15.0,
                "scene_count":
                    5,
                "source_image_storage_keys": [
                    "run-1/ig.jpeg"
                ],
            }
        ],
    }

    refs = [
        ArtifactVersionRef(
            artifact_id="ig-v2",
            artifact_type=(
                ArtifactType
                .PLATFORM_CONTENT
                .value
            ),
            platform="instagram",
            version=2,
        ),
        ArtifactVersionRef(
            artifact_id="x-v3",
            artifact_type=(
                ArtifactType
                .PLATFORM_CONTENT
                .value
            ),
            platform="x",
            version=3,
        ),
        ArtifactVersionRef(
            artifact_id="creative-v4",
            artifact_type=(
                ArtifactType
                .CREATIVE_ASSETS
                .value
            ),
            version=4,
        ),
        ArtifactVersionRef(
            artifact_id="generated-v5",
            artifact_type=(
                ArtifactType
                .GENERATED_ASSETS
                .value
            ),
            version=5,
        ),
    ]

    plan = PublicationPlan(
        plan_id="plan-123",
        run_id="run-1",
        platforms=[
            "instagram",
            "x",
        ],
        artifact_refs=refs,
    )

    payloads = {
        (
            ArtifactType
            .PLATFORM_CONTENT
            .value,
            "instagram",
            2,
        ):
            instagram_payload,
        (
            ArtifactType
            .PLATFORM_CONTENT
            .value,
            "x",
            3,
        ):
            x_payload,
        (
            ArtifactType
            .CREATIVE_ASSETS
            .value,
            None,
            4,
        ):
            creative_payload,
        (
            ArtifactType
            .GENERATED_ASSETS
            .value,
            None,
            5,
        ):
            generated_payload,
    }

    artifacts = []

    for ref in refs:
        artifacts.append(
            FakeArtifact(
                artifact_id=(
                    ref.artifact_id
                ),
                artifact_type=(
                    ref.artifact_type
                ),
                platform=(
                    ref.platform
                ),
                version=(
                    ref.version
                ),
                payload=(
                    payloads[
                        (
                            ref.artifact_type,
                            ref.platform,
                            ref.version,
                        )
                    ]
                ),
            )
        )

    persistence = FakePersistence(
        plan=plan,
        artifacts=artifacts,
        payloads=payloads,
    )

    media_store = (
        RecordingMediaStore(
            package_root
        )
    )

    service = (
        ManualPublishPackageService(
            persistence=persistence,
            media_store=media_store,
            package_root=package_root,
            generated_assets_root=(
                generated_root
            ),
        )
    )

    return (
        service,
        persistence,
        media_store,
        package_root,
    )


def test_manual_package_builds_exact_approved_content_and_media(
    tmp_path,
):

    (
        service,
        persistence,
        media_store,
        package_root,
    ) = build_fixture(
        tmp_path
    )

    package = service.build(
        "run-1"
    )

    root = (
        package_root
        / "run-1"
        / "plan-123"
    )

    assert media_store.verified is True

    assert (
        package.publication_plan_id
        == "plan-123"
    )

    assert package.platforms == [
        "instagram",
        "x",
    ]

    assert (
        root
        / "instagram"
        / "caption.txt"
    ).read_text(
        encoding="utf-8"
    ) == (
        "Approved Instagram caption\n"
    )

    assert (
        root
        / "instagram"
        / "hashtags.txt"
    ).read_text(
        encoding="utf-8"
    ) == "#qa #ai\n"

    assert (
        root
        / "x"
        / "post.txt"
    ).read_text(
        encoding="utf-8"
    ) == "Approved X post\n"

    assert (
        root
        / "x"
        / "thread.txt"
    ).read_text(
        encoding="utf-8"
    ) == (
        "Thread one\n\n"
        "Thread two\n"
    )

    assert (
        root
        / "instagram"
        / "reel_storyboard.json"
    ).is_file()

    assert (
        root
        / "instagram"
        / "media"
        / "carousel_slide_1.jpeg"
    ).read_bytes() == (
        b"instagram-image"
    )

    assert (
        root
        / "x"
        / "media"
        / "supporting_visual.jpeg"
    ).read_bytes() == (
        b"x-image"
    )

    assert (
        root
        / "instagram"
        / "media"
        / "reel_video.mp4"
    ).read_bytes() == (
        b"reel-video"
    )

    assert media_store.calls[-1] == (
        "run-1/plan-123/manifest.json"
    )

    assert (
        persistence.saved[-1][0]
        == ArtifactType
        .MANUAL_PUBLISH_PACKAGE
    )

    assert {
        (
            ArtifactType
            .PLATFORM_CONTENT
            .value,
            "instagram",
            2,
        ),
        (
            ArtifactType
            .PLATFORM_CONTENT
            .value,
            "x",
            3,
        ),
        (
            ArtifactType
            .CREATIVE_ASSETS
            .value,
            None,
            4,
        ),
        (
            ArtifactType
            .GENERATED_ASSETS
            .value,
            None,
            5,
        ),
    }.issubset(
        set(
            persistence
            .version_reads
        )
    )


def test_manual_package_manifest_contains_hashes_and_provenance(
    tmp_path,
):

    (
        service,
        _,
        _,
        package_root,
    ) = build_fixture(
        tmp_path
    )

    package = service.build(
        "run-1"
    )

    root = (
        package_root
        / "run-1"
        / "plan-123"
    )

    manifest = json.loads(
        (
            root
            / "manifest.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    assert (
        manifest[
            "publication_plan_id"
        ]
        == "plan-123"
    )

    manifest_paths = {
        file["relative_path"]
        for file
        in manifest["files"]
    }

    assert (
        "manifest.json"
        not in manifest_paths
    )

    assert (
        "instagram/media/"
        "carousel_slide_1.jpeg"
        in manifest_paths
    )

    assert (
        "instagram/media/"
        "reel_video.mp4"
        in manifest_paths
    )

    media_file = next(
        file
        for file
        in package.files
        if (
            file.relative_path
            == (
                "instagram/media/"
                "carousel_slide_1.jpeg"
            )
        )
    )

    media_bytes = (
        root
        / media_file.relative_path
    ).read_bytes()

    assert (
        media_file.sha256
        == hashlib.sha256(
            media_bytes
        ).hexdigest()
    )

    assert (
        media_file.source_provider
        == "development"
    )

    assert (
        media_file.source_model
        == "deterministic-placeholder-v1"
    )

    assert (
        package.manifest_file
        is not None
    )


def test_manual_package_requires_approved_status(
    tmp_path,
):

    (
        service,
        persistence,
        _,
        _,
    ) = build_fixture(
        tmp_path
    )

    persistence.run.status = (
        RunStatus
        .READY_FOR_HUMAN_REVIEW
        .value
    )

    with pytest.raises(
        ValueError,
        match="approved_for_publishing",
    ):
        service.build(
            "run-1"
        )

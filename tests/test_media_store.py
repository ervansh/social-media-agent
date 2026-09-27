from pathlib import Path

import pytest

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.stored_media import (
    StoredMediaAsset,
)
from social_media_agent.services.media_store.factory import (
    get_media_store,
)
from social_media_agent.services.media_store.local_store import (
    LocalMediaStore,
)
from social_media_agent.services.media_store.s3_store import (
    S3MediaStore,
)


class FakeS3Client:

    def __init__(self):
        self.head_bucket_calls = []
        self.uploads = []
        self.presigned_calls = []

    def head_bucket(
        self,
        *,
        Bucket,
    ):
        self.head_bucket_calls.append(
            Bucket
        )

        return {}

    def upload_file(
        self,
        filename,
        bucket,
        key,
        ExtraArgs=None,
    ):
        self.uploads.append(
            {
                "filename": filename,
                "bucket": bucket,
                "key": key,
                "extra_args": ExtraArgs,
            }
        )

    def generate_presigned_url(
        self,
        operation,
        *,
        Params,
        ExpiresIn,
    ):
        self.presigned_calls.append(
            {
                "operation": operation,
                "params": Params,
                "expires_in": ExpiresIn,
            }
        )

        return (
            "https://signed.example.com/"
            f"{Params['Key']}"
        )


def test_local_media_store_returns_stable_reference(
    tmp_path,
):

    run_dir = (
        tmp_path
        / "run-1"
    )

    run_dir.mkdir()

    image = (
        run_dir
        / "slide.jpeg"
    )

    image.write_bytes(
        b"jpeg-data"
    )

    store = LocalMediaStore(
        local_root=tmp_path
    )

    store.verify_access()

    stored = store.store(
        "run-1/slide.jpeg"
    )

    assert stored == StoredMediaAsset(
        source_storage_key=(
            "run-1/slide.jpeg"
        ),
        store_provider="local",
        object_key=(
            "run-1/slide.jpeg"
        ),
        content_type="image/jpeg",
        size_bytes=9,
    )

    assert (
        store.resolve_path(
            stored
        )
        == image.resolve()
    )


def test_local_media_store_has_no_public_url(
    tmp_path,
):

    store = LocalMediaStore(
        local_root=tmp_path
    )

    media = StoredMediaAsset(
        source_storage_key="run-1/a.jpg",
        store_provider="local",
        object_key="run-1/a.jpg",
        content_type="image/jpeg",
        size_bytes=1,
    )

    with pytest.raises(
        RuntimeError,
        match="does not expose",
    ):
        store.create_download_url(
            media
        )


def test_s3_media_store_uploads_and_returns_reference(
    tmp_path,
):

    run_dir = (
        tmp_path
        / "run-1"
    )

    run_dir.mkdir()

    image = (
        run_dir
        / "slide.jpg"
    )

    image.write_bytes(
        b"fake-jpeg"
    )

    client = FakeS3Client()

    store = S3MediaStore(
        bucket="test-bucket",
        region="ap-south-1",
        prefix="social-media-agent",
        local_root=tmp_path,
        expires_in_seconds=1800,
        client=client,
    )

    store.verify_access()

    stored = store.store(
        "run-1/slide.jpg"
    )

    assert (
        client.head_bucket_calls
        == ["test-bucket"]
    )

    assert stored.store_provider == "s3"
    assert (
        stored.source_storage_key
        == "run-1/slide.jpg"
    )
    assert (
        stored.object_key
        == (
            "social-media-agent/"
            "run-1/slide.jpg"
        )
    )
    assert stored.content_type == "image/jpeg"
    assert stored.size_bytes == 9

    assert len(
        client.uploads
    ) == 1

    upload = client.uploads[0]

    assert Path(
        upload["filename"]
    ) == image

    assert (
        upload["extra_args"][
            "ContentType"
        ]
        == "image/jpeg"
    )

    url = (
        store.create_download_url(
            stored
        )
    )

    assert url == (
        "https://signed.example.com/"
        "social-media-agent/"
        "run-1/slide.jpg"
    )

    assert (
        client.presigned_calls[0][
            "expires_in"
        ]
        == 1800
    )


def test_s3_media_store_rejects_wrong_provider_reference(
    tmp_path,
):

    store = S3MediaStore(
        bucket="test-bucket",
        local_root=tmp_path,
        client=FakeS3Client(),
    )

    media = StoredMediaAsset(
        source_storage_key="run-1/a.jpg",
        store_provider="local",
        object_key="run-1/a.jpg",
        content_type="image/jpeg",
        size_bytes=1,
    )

    with pytest.raises(
        ValueError,
        match="provider mismatch",
    ):
        store.create_download_url(
            media
        )


def test_media_store_factory_selects_local(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "media_store_provider",
        "local",
    )

    store = get_media_store()

    assert isinstance(
        store,
        LocalMediaStore,
    )


def test_media_store_factory_rejects_unknown_provider(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "media_store_provider",
        "unknown",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported MEDIA_STORE_PROVIDER",
    ):
        get_media_store()

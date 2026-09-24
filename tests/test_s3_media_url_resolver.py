from pathlib import Path

from social_media_agent.services.publishing.s3_media_url_resolver import (
    S3MediaUrlResolver,
)


class FakeS3Client:

    def __init__(self):
        self.uploads = []
        self.presigned_calls = []

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


def test_s3_resolver_uploads_and_returns_signed_url(
    tmp_path,
):

    run_dir = tmp_path / "run-1"
    run_dir.mkdir()

    image = run_dir / "slide.jpg"
    image.write_bytes(
        b"fake-jpeg"
    )

    client = FakeS3Client()

    resolver = S3MediaUrlResolver(
        bucket="test-bucket",
        region="ap-south-1",
        prefix="social-media-agent",
        local_root=tmp_path,
        expires_in_seconds=1800,
        client=client,
    )

    url = resolver.resolve(
        "run-1/slide.jpg"
    )

    assert url == (
        "https://signed.example.com/"
        "social-media-agent/"
        "run-1/slide.jpg"
    )

    assert len(client.uploads) == 1

    upload = client.uploads[0]

    assert Path(
        upload["filename"]
    ) == image

    assert (
        upload["bucket"]
        == "test-bucket"
    )

    assert (
        upload["key"]
        == (
            "social-media-agent/"
            "run-1/slide.jpg"
        )
    )

    assert (
        upload["extra_args"][
            "ContentType"
        ]
        == "image/jpeg"
    )

    signed = (
        client.presigned_calls[0]
    )

    assert (
        signed["operation"]
        == "get_object"
    )

    assert (
        signed["expires_in"]
        == 1800
    )


def test_s3_resolver_requires_existing_local_file(
    tmp_path,
):

    resolver = S3MediaUrlResolver(
        bucket="test-bucket",
        local_root=tmp_path,
        client=FakeS3Client(),
    )

    try:
        resolver.resolve(
            "run-1/missing.jpg"
        )

    except FileNotFoundError as exc:
        assert (
            "Generated media file not found"
            in str(exc)
        )

    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )

import pytest

from social_media_agent.models.publication import (
    PublicationRequest,
)
from social_media_agent.services.publishing.instagram_publisher import (
    InstagramPublisher,
)


class FakeResolver:

    def resolve(
        self,
        storage_key: str,
    ) -> str:

        return (
            "https://cdn.example.com/"
            f"{storage_key}"
        )


class FakeInstagramClient:

    def __init__(self):
        self.calls = []
        self.counter = 0

    def create_image_container(
        self,
        *,
        image_url,
        caption=None,
        is_carousel_item=False,
    ):
        self.counter += 1

        container_id = (
            f"container-{self.counter}"
        )

        self.calls.append(
            (
                "create_image",
                image_url,
                caption,
                is_carousel_item,
                container_id,
            )
        )

        return container_id

    def create_carousel_container(
        self,
        *,
        child_container_ids,
        caption,
    ):
        self.calls.append(
            (
                "create_carousel",
                list(child_container_ids),
                caption,
            )
        )

        return "carousel-parent"

    def wait_until_ready(
        self,
        container_id,
    ):
        self.calls.append(
            (
                "wait",
                container_id,
            )
        )

    def publish_container(
        self,
        container_id,
    ):
        self.calls.append(
            (
                "publish",
                container_id,
            )
        )

        return "published-123"


def build_publisher():

    return InstagramPublisher(
        client=FakeInstagramClient(),
        media_url_resolver=FakeResolver(),
    )


def test_instagram_single_image_publish():

    publisher = build_publisher()

    result = publisher.publish(
        PublicationRequest(
            run_id="run-1",
            platform="instagram",
            payload={
                "caption": "Caption"
            },
            media_storage_keys=[
                "run-1/image.jpg"
            ],
        )
    )

    assert result.status == "published"
    assert (
        result.external_id
        == "published-123"
    )
    assert (
        result.response_payload[
            "publication_type"
        ]
        == "image"
    )

    assert (
        ("wait", "container-1")
        in publisher.client.calls
    )

    assert (
        ("publish", "container-1")
        in publisher.client.calls
    )


def test_instagram_carousel_publish():

    publisher = build_publisher()

    result = publisher.publish(
        PublicationRequest(
            run_id="run-1",
            platform="instagram",
            payload={
                "caption": "Carousel"
            },
            media_storage_keys=[
                "run-1/1.jpg",
                "run-1/2.jpeg",
            ],
        )
    )

    assert result.status == "published"

    assert (
        result.response_payload[
            "publication_type"
        ]
        == "carousel"
    )

    assert (
        (
            "wait",
            "carousel-parent",
        )
        in publisher.client.calls
    )


def test_instagram_rejects_non_jpeg_media():

    publisher = build_publisher()

    with pytest.raises(
        ValueError,
        match="requires JPEG media",
    ):
        publisher.publish(
            PublicationRequest(
                run_id="run-1",
                platform="instagram",
                payload={
                    "caption": "Caption"
                },
                media_storage_keys=[
                    "run-1/image.png"
                ],
            )
        )

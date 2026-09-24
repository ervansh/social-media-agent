from social_media_agent.services.publishing.instagram_graph_client import (
    InstagramGraphClient,
)


class FakeResponse:

    def __init__(
        self,
        payload,
        *,
        ok=True,
    ):
        self._payload = payload
        self.ok = ok

    def json(self):
        return self._payload


class FakeSession:

    def __init__(self):
        self.calls = []
        self.container_counter = 0

    def request(
        self,
        *,
        method,
        url,
        headers,
        data=None,
        params=None,
        timeout=None,
    ):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "data": data,
                "params": params,
                "timeout": timeout,
            }
        )

        if (
            method == "POST"
            and url.endswith(
                "/ig-user-1/media"
            )
        ):
            self.container_counter += 1

            return FakeResponse(
                {
                    "id": (
                        "container-"
                        f"{self.container_counter}"
                    )
                }
            )

        if (
            method == "GET"
            and "/container-" in url
        ):
            return FakeResponse(
                {
                    "status_code":
                        "FINISHED",
                    "status":
                        "Finished",
                }
            )

        if (
            method == "POST"
            and url.endswith(
                "/ig-user-1/media_publish"
            )
        ):
            return FakeResponse(
                {
                    "id": "media-456"
                }
            )

        raise AssertionError(
            f"Unexpected request: "
            f"{method} {url}"
        )


def build_client():

    return InstagramGraphClient(
        base_url=(
            "https://graph.facebook.com"
        ),
        api_version="v26.0",
        instagram_user_id="ig-user-1",
        access_token="fake-token",
        timeout_seconds=60,
        session=FakeSession(),
    )


def test_create_image_container():

    client = build_client()

    container_id = (
        client.create_image_container(
            image_url=(
                "https://cdn.example.com/"
                "image.jpg"
            ),
            caption="Test caption",
        )
    )

    assert container_id == "container-1"

    call = client.session.calls[0]

    assert (
        call["headers"]["Authorization"]
        == "Bearer fake-token"
    )

    assert call["data"] == {
        "image_url": (
            "https://cdn.example.com/"
            "image.jpg"
        ),
        "caption": "Test caption",
    }


def test_create_carousel_container():

    client = build_client()

    container_id = (
        client.create_carousel_container(
            child_container_ids=[
                "child-1",
                "child-2",
            ],
            caption="Carousel",
        )
    )

    assert container_id == "container-1"

    call = client.session.calls[0]

    assert (
        call["data"]["media_type"]
        == "CAROUSEL"
    )

    assert (
        call["data"]["children"]
        == "child-1,child-2"
    )


def test_wait_until_ready():

    client = build_client()

    client.wait_until_ready(
        "container-1"
    )

    assert (
        client.session.calls[0][
            "params"
        ]["fields"]
        == "status_code,status"
    )


def test_publish_container():

    client = build_client()

    media_id = (
        client.publish_container(
            "container-1"
        )
    )

    assert media_id == "media-456"

    call = client.session.calls[0]

    assert call["data"] == {
        "creation_id": "container-1"
    }

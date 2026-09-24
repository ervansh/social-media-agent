from social_media_agent.services.publishing.instagram_preflight import (
    InstagramPublishingPreflight,
)


class FakeInstagramClient:

    def get_account_info(self):
        return {
            "id": "ig-123",
            "username": "qa_account",
            "media_count": 42,
        }


class FakeResolver:

    def resolve(
        self,
        storage_key,
    ):
        return (
            "https://cdn.example.com/"
            f"{storage_key}"
        )


class FakeResponse:

    def __init__(
        self,
        status_code,
    ):
        self.status_code = status_code


class FakeHttpSession:

    def __init__(
        self,
        status_code=200,
    ):
        self.status_code = status_code
        self.calls = []

    def get(
        self,
        url,
        *,
        stream,
        allow_redirects,
        timeout,
    ):
        self.calls.append(
            {
                "url": url,
                "stream": stream,
                "allow_redirects":
                    allow_redirects,
                "timeout": timeout,
            }
        )

        return FakeResponse(
            self.status_code
        )


def test_preflight_verifies_account_only():

    service = (
        InstagramPublishingPreflight(
            client=FakeInstagramClient(),
            media_url_resolver=(
                FakeResolver()
            ),
            http_session=(
                FakeHttpSession()
            ),
        )
    )

    result = service.verify()

    assert result.account_id == "ig-123"
    assert result.username == "qa_account"
    assert result.media_count == 42
    assert result.media_url is None
    assert (
        result.media_url_accessible
        is False
    )


def test_preflight_verifies_public_media_url():

    http = FakeHttpSession(
        status_code=200
    )

    service = (
        InstagramPublishingPreflight(
            client=FakeInstagramClient(),
            media_url_resolver=(
                FakeResolver()
            ),
            http_session=http,
        )
    )

    result = service.verify(
        storage_key=(
            "run-1/image.jpg"
        )
    )

    assert result.media_url == (
        "https://cdn.example.com/"
        "run-1/image.jpg"
    )

    assert (
        result.media_url_accessible
        is True
    )

    assert (
        http.calls[0]["url"]
        == result.media_url
    )


def test_preflight_rejects_inaccessible_media():

    service = (
        InstagramPublishingPreflight(
            client=FakeInstagramClient(),
            media_url_resolver=(
                FakeResolver()
            ),
            http_session=(
                FakeHttpSession(
                    status_code=403
                )
            ),
        )
    )

    try:
        service.verify(
            storage_key=(
                "run-1/image.jpg"
            )
        )

    except RuntimeError as exc:
        assert (
            "not publicly accessible"
            in str(exc)
        )

    else:
        raise AssertionError(
            "Expected RuntimeError"
        )

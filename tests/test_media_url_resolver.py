import pytest

from social_media_agent.services.publishing.media_url_resolver import (
    PublicBaseUrlMediaUrlResolver,
)


def test_media_url_resolver_builds_public_url():

    resolver = PublicBaseUrlMediaUrlResolver(
        base_url="https://cdn.example.com/assets"
    )

    result = resolver.resolve(
        "run-1/slide 1.jpg"
    )

    assert result == (
        "https://cdn.example.com/assets/"
        "run-1/slide%201.jpg"
    )


def test_media_url_resolver_rejects_traversal():

    resolver = PublicBaseUrlMediaUrlResolver(
        base_url="https://cdn.example.com"
    )

    with pytest.raises(
        ValueError,
        match="invalid path segment",
    ):
        resolver.resolve(
            "../secret.jpg"
        )


def test_media_url_resolver_requires_base_url():

    resolver = PublicBaseUrlMediaUrlResolver(
        base_url=""
    )

    with pytest.raises(
        ValueError,
        match="PUBLIC_MEDIA_BASE_URL",
    ):
        resolver.resolve(
            "run-1/image.jpg"
        )

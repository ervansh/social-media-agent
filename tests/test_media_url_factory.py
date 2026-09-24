from social_media_agent.services.publishing.media_url_factory import (
    get_media_url_resolver,
)
from social_media_agent.services.publishing.media_url_resolver import (
    PublicBaseUrlMediaUrlResolver,
)


def test_media_url_factory_uses_public_base_url(
    monkeypatch,
):

    monkeypatch.setattr(
        "social_media_agent.services."
        "publishing.media_url_factory."
        "settings.media_url_provider",
        "public_base_url",
    )

    resolver = get_media_url_resolver()

    assert isinstance(
        resolver,
        PublicBaseUrlMediaUrlResolver,
    )

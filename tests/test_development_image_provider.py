import io

from PIL import Image

from social_media_agent.services.image.development_provider import (
    DevelopmentImageProvider,
)
from social_media_agent.services.image.factory import (
    get_image_provider,
)


def test_development_provider_returns_valid_jpeg():

    provider = DevelopmentImageProvider()

    result = provider.generate(
        prompt=(
            "AI automation testing "
            "carousel visual"
        ),
        width=1080,
        height=1350,
    )

    assert result.provider == "development"
    assert (
        result.model
        == "deterministic-placeholder-v1"
    )
    assert result.file_extension == "jpeg"
    assert result.width == 1080
    assert result.height == 1350

    image = Image.open(
        io.BytesIO(
            result.image_bytes
        )
    )

    assert image.format == "JPEG"
    assert image.size == (
        1080,
        1350,
    )


def test_development_provider_is_deterministic():

    provider = DevelopmentImageProvider()

    first = provider.generate(
        prompt="same prompt",
        width=600,
        height=800,
    )

    second = provider.generate(
        prompt="same prompt",
        width=600,
        height=800,
    )

    assert (
        first.image_bytes
        == second.image_bytes
    )


def test_image_factory_selects_development_provider(
    monkeypatch,
):

    monkeypatch.setattr(
        "social_media_agent.services."
        "image.factory.settings.image_provider",
        "development",
    )

    provider = get_image_provider()

    assert isinstance(
        provider,
        DevelopmentImageProvider,
    )

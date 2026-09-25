import base64
import io

import pytest
from PIL import Image

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.factory import (
    get_image_provider,
)
from social_media_agent.services.image.openai_provider import (
    OpenAIImageAPIError,
    OpenAIImageProvider,
)


def make_jpeg(
    width: int,
    height: int,
) -> bytes:

    image = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    output = io.BytesIO()

    image.save(
        output,
        format="JPEG",
        quality=90,
    )

    return output.getvalue()


class FakeResponse:

    def __init__(
        self,
        payload,
        *,
        ok=True,
        status_code=200,
    ):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:

    def __init__(
        self,
        response,
    ):
        self.response = response
        self.calls = []

    def post(
        self,
        url,
        *,
        headers,
        json,
        timeout,
    ):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )

        return self.response


def configure_openai_image_settings(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "openai_image_output_format",
        "jpeg",
    )

    monkeypatch.setattr(
        settings,
        "openai_image_quality",
        "medium",
    )

    monkeypatch.setattr(
        settings,
        "openai_image_background",
        "opaque",
    )

    monkeypatch.setattr(
        settings,
        "openai_image_output_compression",
        90,
    )

    monkeypatch.setattr(
        settings,
        "image_size_multiple",
        16,
    )


def test_openai_provider_generates_valid_jpeg(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    image_bytes = make_jpeg(
        1088,
        1360,
    )

    session = FakeSession(
        FakeResponse(
            {
                "data": [
                    {
                        "b64_json":
                            base64.b64encode(
                                image_bytes
                            ).decode("ascii")
                    }
                ]
            }
        )
    )

    provider = OpenAIImageProvider(
        session=session,
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        model="gpt-image-2.5-flare",
    )

    result = provider.generate(
        prompt="Create a QA carousel image.",
        width=1080,
        height=1350,
    )

    assert result.provider == "openai"
    assert (
        result.model
        == "gpt-image-2.5-flare"
    )
    assert result.file_extension == "jpeg"
    assert result.width == 1088
    assert result.height == 1360

    call = session.calls[0]

    assert (
        call["url"]
        == (
            "https://api.openai.com/v1"
            "/images/generations"
        )
    )

    assert (
        call["headers"]["Authorization"]
        == "Bearer test-key"
    )

    assert call["json"] == {
        "model":
            "gpt-image-2.5-flare",
        "prompt":
            "Create a QA carousel image.",
        "size":
            "1088x1360",
        "quality":
            "medium",
        "output_format":
            "jpeg",
        "background":
            "opaque",
        "n":
            1,
        "output_compression":
            90,
    }


def test_openai_provider_rejects_invalid_dimensions(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    provider = OpenAIImageProvider(
        session=FakeSession(
            FakeResponse({})
        ),
        api_key="test-key",
        model="gpt-image-2.5-flare",
    )

    with pytest.raises(
        ValueError,
        match="cannot exceed 3840",
    ):
        provider.generate(
            prompt="Image",
            width=4000,
            height=1000,
        )


def test_openai_provider_surfaces_api_error(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    session = FakeSession(
        FakeResponse(
            {
                "error": {
                    "message":
                        "Organization verification required.",
                    "type":
                        "invalid_request_error",
                    "code":
                        "verification_required",
                }
            },
            ok=False,
            status_code=403,
        )
    )

    provider = OpenAIImageProvider(
        session=session,
        api_key="test-key",
        model="gpt-image-2.5-flare",
    )

    with pytest.raises(
        OpenAIImageAPIError,
        match="verification_required",
    ):
        provider.generate(
            prompt="Image",
            width=1024,
            height=1024,
        )


def test_openai_provider_rejects_invalid_image_bytes(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    session = FakeSession(
        FakeResponse(
            {
                "data": [
                    {
                        "b64_json":
                            base64.b64encode(
                                b"not-an-image"
                            ).decode("ascii")
                    }
                ]
            }
        )
    )

    provider = OpenAIImageProvider(
        session=session,
        api_key="test-key",
        model="gpt-image-2.5-flare",
    )

    with pytest.raises(
        OpenAIImageAPIError,
        match="invalid image bytes",
    ):
        provider.generate(
            prompt="Image",
            width=1024,
            height=1024,
        )


def test_openai_provider_rejects_transparent_jpeg(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    monkeypatch.setattr(
        settings,
        "openai_image_background",
        "transparent",
    )

    with pytest.raises(
        ValueError,
        match="requires PNG or WebP",
    ):
        OpenAIImageProvider(
            session=FakeSession(
                FakeResponse({})
            ),
            api_key="test-key",
            model="gpt-image-2.5-flare",
        )


def test_image_factory_selects_openai_provider(
    monkeypatch,
):

    configure_openai_image_settings(
        monkeypatch
    )

    monkeypatch.setattr(
        settings,
        "image_provider",
        "openai",
    )

    monkeypatch.setattr(
        settings,
        "openai_api_key",
        "test-key",
    )

    monkeypatch.setattr(
        settings,
        "openai_image_model",
        "gpt-image-2.5-flare",
    )

    provider = get_image_provider()

    assert isinstance(
        provider,
        OpenAIImageProvider,
    )

    assert (
        provider.PROVIDER_NAME
        == "openai"
    )

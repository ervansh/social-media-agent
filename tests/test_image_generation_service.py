import pytest

from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    ImageBrief,
)
from social_media_agent.services.image.base import (
    ImageGenerationResult,
)
from social_media_agent.services.image_generation.creative_image_service import (
    CreativeImageGenerationService,
)


class FakeImageProvider:

    PROVIDER_NAME = "fake"

    def __init__(self):
        self.prompts = []

    def generate(
        self,
        prompt,
        width,
        height,
    ):
        self.prompts.append(
            prompt
        )

        return ImageGenerationResult(
            image_bytes=b"fake-image-data",
            width=width,
            height=height,
            provider="fake",
            model="fake-model",
            file_extension="png",
        )


def test_creative_image_generation_service(
    tmp_path,
):

    creative_assets = (
        CreativeAssetBundle(
            images=[
                ImageBrief(
                    platform="youtube",
                    asset_type="thumbnail",
                    width=3840,
                    height=2160,
                    objective=(
                        "Create thumbnail"
                    ),
                    visual_concept=(
                        "QA engineer with AI"
                    ),
                    text_overlay=(
                        "AI TESTING?"
                    ),
                    image_prompt=(
                        "Professional QA engineer "
                        "reviewing AI tests"
                    ),
                    negative_prompt=(
                        "clutter, unreadable text"
                    ),
                )
            ]
        )
    )

    provider = FakeImageProvider()

    service = (
        CreativeImageGenerationService(
            provider=provider,
            output_root=tmp_path,
        )
    )

    result = service.generate(
        run_id="test-run",
        creative_assets=creative_assets,
    )

    assert len(result.images) == 1

    generated = result.images[0]

    assert generated.platform == "youtube"
    assert generated.provider == "fake"
    assert service.provider_name == "fake"

    expected_file = (
        tmp_path
        / generated.storage_key
    )

    assert expected_file.exists()

    assert (
        expected_file.read_bytes()
        == b"fake-image-data"
    )

    assert len(provider.prompts) == 1

    prompt = provider.prompts[0]

    assert (
        'Render the following text exactly once, '
        'clearly and legibly: "AI TESTING?"'
        in prompt
    )

    assert (
        "Avoid the following: "
        "clutter, unreadable text"
        in prompt
    )


class FailOnSecondImageProvider:

    PROVIDER_NAME = "fake"

    def __init__(self):
        self.calls = 0

    def generate(
        self,
        prompt,
        width,
        height,
    ):
        self.calls += 1

        if self.calls == 2:
            raise RuntimeError(
                "provider failure"
            )

        return ImageGenerationResult(
            image_bytes=b"first-image",
            width=width,
            height=height,
            provider="fake",
            model="fake-model",
            file_extension="jpeg",
        )


def test_creative_image_generation_cleans_partial_files_on_failure(
    tmp_path,
):

    creative_assets = CreativeAssetBundle(
        images=[
            ImageBrief(
                platform="instagram",
                asset_type="carousel_slide_1",
                width=1080,
                height=1350,
                objective="Slide one",
                visual_concept="Concept one",
                image_prompt="Prompt one",
            ),
            ImageBrief(
                platform="instagram",
                asset_type="carousel_slide_2",
                width=1080,
                height=1350,
                objective="Slide two",
                visual_concept="Concept two",
                image_prompt="Prompt two",
            ),
        ]
    )

    service = CreativeImageGenerationService(
        provider=FailOnSecondImageProvider(),
        output_root=tmp_path,
    )

    with pytest.raises(
        RuntimeError,
        match="provider failure",
    ):
        service.generate(
            run_id="test-run",
            creative_assets=creative_assets,
        )

    run_directory = (
        tmp_path
        / "test-run"
    )

    assert run_directory.exists()

    assert list(
        run_directory.iterdir()
    ) == []

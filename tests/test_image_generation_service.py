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

    def generate(
        self,
        prompt,
        width,
        height,
    ):
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
                )
            ]
        )
    )

    service = (
        CreativeImageGenerationService(
            provider=FakeImageProvider(),
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

    expected_file = (
        tmp_path
        / generated.storage_key
    )

    assert expected_file.exists()

    assert (
        expected_file.read_bytes()
        == b"fake-image-data"
    )
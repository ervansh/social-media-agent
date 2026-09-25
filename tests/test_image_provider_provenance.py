from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    ImageBrief,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
    GeneratedImageAsset,
)
from social_media_agent.services.pipeline.content_pipeline_service import (
    ContentPipelineService,
)


class FakeImageGenerationService:

    def __init__(
        self,
        provider_name: str,
    ):
        self.provider_name = provider_name


def creative_bundle():

    return CreativeAssetBundle(
        images=[
            ImageBrief(
                platform="instagram",
                asset_type="carousel_slide_1",
                width=1080,
                height=1350,
                objective="Create slide",
                visual_concept="QA workflow",
                image_prompt="QA workflow",
            )
        ]
    )


def generated_payload(
    provider: str,
):

    bundle = GeneratedAssetBundle(
        images=[
            GeneratedImageAsset(
                platform="instagram",
                asset_type="carousel_slide_1",
                storage_key="run-1/slide.jpeg",
                provider=provider,
                model="model",
                requested_width=1080,
                requested_height=1350,
                generated_width=1080,
                generated_height=1350,
                prompt="QA workflow",
            )
        ]
    )

    return bundle.model_dump(
        mode="json"
    )


def test_generated_assets_refresh_when_provider_changes():

    result = (
        ContentPipelineService
        ._generated_assets_need_refresh(
            generated_payload=(
                generated_payload(
                    "development"
                )
            ),
            creative_assets=(
                creative_bundle()
            ),
            creative_changed=False,
            image_generation_service=(
                FakeImageGenerationService(
                    "openai"
                )
            ),
        )
    )

    assert result is True


def test_generated_assets_reused_when_provider_matches():

    result = (
        ContentPipelineService
        ._generated_assets_need_refresh(
            generated_payload=(
                generated_payload(
                    "openai"
                )
            ),
            creative_assets=(
                creative_bundle()
            ),
            creative_changed=False,
            image_generation_service=(
                FakeImageGenerationService(
                    "openai"
                )
            ),
        )
    )

    assert result is False


def test_generated_assets_refresh_when_creative_changes():

    result = (
        ContentPipelineService
        ._generated_assets_need_refresh(
            generated_payload=(
                generated_payload(
                    "openai"
                )
            ),
            creative_assets=(
                creative_bundle()
            ),
            creative_changed=True,
            image_generation_service=(
                FakeImageGenerationService(
                    "openai"
                )
            ),
        )
    )

    assert result is True

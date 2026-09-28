from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    StoryboardScene,
    VideoStoryboard,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
    GeneratedImageAsset,
    GeneratedVideoAsset,
)
from social_media_agent.services.pipeline.content_pipeline_service import (
    ContentPipelineService,
)


class FakeVideoRenderer:

    PROVIDER_NAME = "ffmpeg"
    MODEL_NAME = (
        "deterministic-still-motion-v1"
    )

    @property
    def provider_name(
        self,
    ):
        return self.PROVIDER_NAME


def _creative():

    return CreativeAssetBundle(
        storyboards=[
            VideoStoryboard(
                platform="instagram",
                asset_type="reel_storyboard",
                scenes=[
                    StoryboardScene(
                        scene_number=1,
                        narration="Point",
                        visual_direction="Visual",
                    )
                ],
            )
        ]
    )


def _generated(
    *,
    video_provider="ffmpeg",
    video_model=(
        "deterministic-still-motion-v1"
    ),
    include_video=True,
):

    videos = []

    if include_video:
        videos.append(
            GeneratedVideoAsset(
                platform="instagram",
                asset_type="reel_video",
                storyboard_asset_type=(
                    "reel_storyboard"
                ),
                storage_key=(
                    "run-1/reel.mp4"
                ),
                provider=video_provider,
                model=video_model,
                width=1080,
                height=1920,
                fps=30,
                duration_seconds=3.0,
                scene_count=1,
                source_image_storage_keys=[
                    "run-1/slide.jpeg"
                ],
            )
        )

    return GeneratedAssetBundle(
        images=[
            GeneratedImageAsset(
                platform="instagram",
                asset_type=(
                    "carousel_slide_1"
                ),
                storage_key=(
                    "run-1/slide.jpeg"
                ),
                provider="development",
                model=(
                    "deterministic-placeholder-v1"
                ),
                requested_width=1080,
                requested_height=1350,
                generated_width=1080,
                generated_height=1350,
                prompt="Prompt",
            )
        ],
        videos=videos,
    )


def test_video_refresh_required_when_video_missing():

    assert (
        ContentPipelineService
        ._generated_videos_need_refresh(
            generated_payload=(
                _generated(
                    include_video=False
                ).model_dump(
                    mode="json"
                )
            ),
            creative_assets=_creative(),
            creative_changed=False,
            video_rendering_service=(
                FakeVideoRenderer()
            ),
        )
        is True
    )


def test_video_refresh_not_required_when_current():

    assert (
        ContentPipelineService
        ._generated_videos_need_refresh(
            generated_payload=(
                _generated()
                .model_dump(
                    mode="json"
                )
            ),
            creative_assets=_creative(),
            creative_changed=False,
            video_rendering_service=(
                FakeVideoRenderer()
            ),
        )
        is False
    )


def test_video_refresh_required_when_creative_changes():

    assert (
        ContentPipelineService
        ._generated_videos_need_refresh(
            generated_payload=(
                _generated()
                .model_dump(
                    mode="json"
                )
            ),
            creative_assets=_creative(),
            creative_changed=True,
            video_rendering_service=(
                FakeVideoRenderer()
            ),
        )
        is True
    )


def test_video_refresh_required_for_renderer_change():

    assert (
        ContentPipelineService
        ._generated_videos_need_refresh(
            generated_payload=(
                _generated(
                    video_provider="other"
                ).model_dump(
                    mode="json"
                )
            ),
            creative_assets=_creative(),
            creative_changed=False,
            video_rendering_service=(
                FakeVideoRenderer()
            ),
        )
        is True
    )


def test_no_video_refresh_without_reel_storyboard():

    assert (
        ContentPipelineService
        ._generated_videos_need_refresh(
            generated_payload=None,
            creative_assets=(
                CreativeAssetBundle()
            ),
            creative_changed=True,
            video_rendering_service=(
                FakeVideoRenderer()
            ),
        )
        is False
    )

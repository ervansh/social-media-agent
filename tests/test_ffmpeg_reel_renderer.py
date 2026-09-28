from pathlib import Path

import pytest
from PIL import Image

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    StoryboardScene,
    VideoStoryboard,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
    GeneratedImageAsset,
)
from social_media_agent.services.video.ffmpeg_reel_renderer import (
    DeterministicReelRenderer,
)


class FakeCommandRunner:

    def __init__(
        self,
        *,
        fail_on_scene: int | None = None,
    ):
        self.calls = []
        self.fail_on_scene = fail_on_scene
        self.scene_calls = 0

    def run(
        self,
        args,
        *,
        cwd=None,
    ):
        self.calls.append(
            {
                "args": list(args),
                "cwd": cwd,
            }
        )

        if args[-1] == "-version":
            return

        output = Path(
            args[-1]
        )

        if cwd is not None:
            output = (
                Path(cwd)
                / output
            )

        if "libx264" in args:
            self.scene_calls += 1

            if (
                self.fail_on_scene
                == self.scene_calls
            ):
                raise RuntimeError(
                    "fake ffmpeg failure"
                )

            output.write_bytes(
                (
                    "scene-"
                    f"{self.scene_calls}"
                ).encode(
                    "utf-8"
                )
            )

            return

        if "concat" in args:
            output.write_bytes(
                b"assembled-video"
            )


def _write_image(
    path: Path,
    *,
    width: int = 1080,
    height: int = 1350,
):
    Image.new(
        "RGB",
        (
            width,
            height,
        ),
        (
            240,
            240,
            240,
        ),
    ).save(
        path,
        format="JPEG",
    )


def _build_inputs(
    tmp_path,
):

    run_id = "run-1"

    run_dir = (
        tmp_path
        / run_id
    )

    run_dir.mkdir()

    image_1 = (
        run_dir
        / "slide-1.jpeg"
    )

    image_2 = (
        run_dir
        / "slide-2.jpeg"
    )

    _write_image(
        image_1
    )

    _write_image(
        image_2
    )

    creative = CreativeAssetBundle(
        storyboards=[
            VideoStoryboard(
                platform="instagram",
                asset_type="reel_storyboard",
                scenes=[
                    StoryboardScene(
                        scene_number=1,
                        narration=(
                            "First grounded point."
                        ),
                        visual_direction=(
                            "Show first QA visual."
                        ),
                        on_screen_text=(
                            "FIRST POINT"
                        ),
                    ),
                    StoryboardScene(
                        scene_number=2,
                        narration=(
                            "Second grounded point."
                        ),
                        visual_direction=(
                            "Show second QA visual."
                        ),
                        on_screen_text=(
                            "SECOND POINT"
                        ),
                    ),
                ],
            )
        ]
    )

    generated = GeneratedAssetBundle(
        images=[
            GeneratedImageAsset(
                platform="instagram",
                asset_type=(
                    "carousel_slide_1"
                ),
                storage_key=(
                    f"{run_id}/"
                    "slide-1.jpeg"
                ),
                provider="development",
                model=(
                    "deterministic-"
                    "placeholder-v1"
                ),
                requested_width=1080,
                requested_height=1350,
                generated_width=1080,
                generated_height=1350,
                prompt="Prompt 1",
            ),
            GeneratedImageAsset(
                platform="instagram",
                asset_type=(
                    "carousel_slide_2"
                ),
                storage_key=(
                    f"{run_id}/"
                    "slide-2.jpeg"
                ),
                provider="development",
                model=(
                    "deterministic-"
                    "placeholder-v1"
                ),
                requested_width=1080,
                requested_height=1350,
                generated_width=1080,
                generated_height=1350,
                prompt="Prompt 2",
            ),
        ]
    )

    return (
        run_id,
        creative,
        generated,
    )


def test_ffmpeg_reel_renderer_creates_generated_video_asset(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "instagram_reel_width",
        360,
    )

    monkeypatch.setattr(
        settings,
        "instagram_reel_height",
        640,
    )

    monkeypatch.setattr(
        settings,
        "reel_text_font_size",
        28,
    )

    monkeypatch.setattr(
        settings,
        "reel_text_margin",
        24,
    )

    (
        run_id,
        creative,
        generated,
    ) = _build_inputs(
        tmp_path
    )

    runner = FakeCommandRunner()

    renderer = (
        DeterministicReelRenderer(
            output_root=tmp_path,
            source_root=tmp_path,
            command_runner=runner,
            ffmpeg_binary="ffmpeg-test",
        )
    )

    result = renderer.render(
        run_id=run_id,
        creative_assets=creative,
        generated_assets=generated,
    )

    assert len(
        result.images
    ) == 2

    assert len(
        result.videos
    ) == 1

    video = result.videos[0]

    assert video.platform == "instagram"
    assert video.asset_type == "reel_video"

    assert (
        video.storyboard_asset_type
        == "reel_storyboard"
    )

    assert video.provider == "ffmpeg"

    assert (
        video.model
        == (
            "deterministic-"
            "still-motion-v1"
        )
    )

    assert video.width == 360
    assert video.height == 640

    assert video.scene_count == 2

    assert (
        video.duration_seconds
        == pytest.approx(
            2
            * settings
            .reel_scene_duration_seconds
        )
    )

    assert (
        video.source_image_storage_keys
        == [
            "run-1/slide-1.jpeg",
            "run-1/slide-2.jpeg",
        ]
    )

    output = (
        tmp_path
        / video.storage_key
    )

    assert output.is_file()

    assert (
        output.read_bytes()
        == b"assembled-video"
    )

    # version + 2 scene clips + concat
    assert len(
        runner.calls
    ) == 4


def test_ffmpeg_reel_renderer_reuses_deterministic_output(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "instagram_reel_width",
        360,
    )

    monkeypatch.setattr(
        settings,
        "instagram_reel_height",
        640,
    )

    monkeypatch.setattr(
        settings,
        "reel_text_font_size",
        28,
    )

    (
        run_id,
        creative,
        generated,
    ) = _build_inputs(
        tmp_path
    )

    runner = FakeCommandRunner()

    renderer = (
        DeterministicReelRenderer(
            output_root=tmp_path,
            source_root=tmp_path,
            command_runner=runner,
            ffmpeg_binary="ffmpeg-test",
        )
    )

    first = renderer.render(
        run_id=run_id,
        creative_assets=creative,
        generated_assets=generated,
    )

    call_count = len(
        runner.calls
    )

    second = renderer.render(
        run_id=run_id,
        creative_assets=creative,
        generated_assets=first,
    )

    assert (
        second.videos[0].storage_key
        == first.videos[0].storage_key
    )

    # Availability check occurs, but existing
    # deterministic MP4 is reused.
    assert len(
        runner.calls
    ) == call_count + 1


def test_ffmpeg_reel_renderer_requires_instagram_images(
    tmp_path,
):

    creative = CreativeAssetBundle(
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

    renderer = (
        DeterministicReelRenderer(
            output_root=tmp_path,
            source_root=tmp_path,
            command_runner=(
                FakeCommandRunner()
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match=(
            "requires generated "
            "Instagram images"
        ),
    ):
        renderer.render(
            run_id="run-1",
            creative_assets=creative,
            generated_assets=(
                GeneratedAssetBundle()
            ),
        )


def test_ffmpeg_reel_renderer_cleans_staging_on_failure(
    tmp_path,
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "instagram_reel_width",
        360,
    )

    monkeypatch.setattr(
        settings,
        "instagram_reel_height",
        640,
    )

    monkeypatch.setattr(
        settings,
        "reel_text_font_size",
        28,
    )

    (
        run_id,
        creative,
        generated,
    ) = _build_inputs(
        tmp_path
    )

    runner = FakeCommandRunner(
        fail_on_scene=2
    )

    renderer = (
        DeterministicReelRenderer(
            output_root=tmp_path,
            source_root=tmp_path,
            command_runner=runner,
        )
    )

    with pytest.raises(
        RuntimeError,
        match="fake ffmpeg failure",
    ):
        renderer.render(
            run_id=run_id,
            creative_assets=creative,
            generated_assets=generated,
        )

    run_dir = (
        tmp_path
        / run_id
    )

    assert not list(
        run_dir.glob(
            ".reel-*"
        )
    )

    assert not list(
        run_dir.glob(
            "instagram_reel_*.mp4"
        )
    )

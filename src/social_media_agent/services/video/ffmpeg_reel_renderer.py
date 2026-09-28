import hashlib
import json
import re
import shutil
from pathlib import Path
from uuid import uuid4

from PIL import (
    Image,
    ImageDraw,
    ImageFilter,
    ImageFont,
    ImageOps,
)

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
    GeneratedVideoAsset,
)
from social_media_agent.services.media_store.local_store import (
    LocalMediaStore,
)
from social_media_agent.services.video.runner import (
    CommandRunner,
    SubprocessCommandRunner,
)


class DeterministicReelRenderer:

    PROVIDER_NAME = "ffmpeg"
    MODEL_NAME = (
        "deterministic-still-motion-v1"
    )

    def __init__(
        self,
        *,
        output_root: str | Path | None = None,
        source_root: str | Path | None = None,
        command_runner: CommandRunner | None = None,
        ffmpeg_binary: str | None = None,
    ):
        self.output_root = Path(
            output_root
            if output_root is not None
            else settings.generated_assets_dir
        ).resolve()

        self.source_store = LocalMediaStore(
            local_root=(
                source_root
                if source_root is not None
                else settings.generated_assets_dir
            )
        )

        self.command_runner = (
            command_runner
            if command_runner is not None
            else SubprocessCommandRunner()
        )

        self.ffmpeg_binary = (
            ffmpeg_binary
            if ffmpeg_binary is not None
            else settings.ffmpeg_binary
        )

        self._validate_settings()

    @staticmethod
    def _validate_settings(
    ) -> None:

        if (
            settings.instagram_reel_width
            <= 0
            or settings.instagram_reel_height
            <= 0
        ):
            raise ValueError(
                "Instagram Reel dimensions "
                "must be positive."
            )

        if settings.reel_fps <= 0:
            raise ValueError(
                "REEL_FPS must be greater "
                "than zero."
            )

        if (
            settings
            .reel_scene_duration_seconds
            <= 0
        ):
            raise ValueError(
                "REEL_SCENE_DURATION_SECONDS "
                "must be greater than zero."
            )

        if (
            settings
            .reel_transition_seconds
            < 0
        ):
            raise ValueError(
                "REEL_TRANSITION_SECONDS "
                "cannot be negative."
            )

        if not (
            0
            <= settings.reel_video_crf
            <= 51
        ):
            raise ValueError(
                "REEL_VIDEO_CRF must be "
                "between 0 and 51."
            )

        if not (
            settings
            .reel_video_preset
            .strip()
        ):
            raise ValueError(
                "REEL_VIDEO_PRESET cannot "
                "be empty."
            )

        if (
            settings
            .reel_text_font_size
            <= 0
        ):
            raise ValueError(
                "REEL_TEXT_FONT_SIZE must "
                "be greater than zero."
            )

        if (
            settings.reel_text_margin
            < 0
            or (
                2
                * settings.reel_text_margin
                >= settings
                .instagram_reel_width
            )
        ):
            raise ValueError(
                "REEL_TEXT_MARGIN must leave "
                "positive horizontal text space."
            )

    @property
    def provider_name(
        self,
    ) -> str:

        return self.PROVIDER_NAME

    def verify_available(
        self,
    ) -> None:

        self.command_runner.run(
            [
                self.ffmpeg_binary,
                "-version",
            ]
        )

    def render(
        self,
        *,
        run_id: str,
        creative_assets: CreativeAssetBundle,
        generated_assets: GeneratedAssetBundle,
    ) -> GeneratedAssetBundle:

        storyboards = [
            storyboard
            for storyboard
            in creative_assets.storyboards
            if (
                storyboard.platform
                == "instagram"
                and storyboard.asset_type
                == "reel_storyboard"
            )
        ]

        if not storyboards:
            return generated_assets

        images = sorted(
            [
                image
                for image
                in generated_assets.images
                if image.platform
                == "instagram"
            ],
            key=self._image_sort_key,
        )

        if not images:
            raise ValueError(
                "Instagram Reel rendering "
                "requires generated Instagram "
                "images."
            )

        self.verify_available()

        videos = list(
            generated_assets.videos
        )

        for storyboard in storyboards:

            video = self._render_storyboard(
                run_id=run_id,
                storyboard=storyboard,
                images=images,
            )

            videos = [
                existing
                for existing in videos
                if not (
                    existing.platform
                    == video.platform
                    and existing.asset_type
                    == video.asset_type
                )
            ]

            videos.append(
                video
            )

        return GeneratedAssetBundle(
            images=generated_assets.images,
            videos=videos,
        )

    def _render_storyboard(
        self,
        *,
        run_id: str,
        storyboard: VideoStoryboard,
        images: list[GeneratedImageAsset],
    ) -> GeneratedVideoAsset:

        scene_images = [
            images[
                index
                % len(images)
            ]
            for index, _
            in enumerate(
                storyboard.scenes
            )
        ]

        source_keys = [
            image.storage_key
            for image
            in scene_images
        ]

        digest = self._render_digest(
            storyboard=storyboard,
            source_keys=source_keys,
        )

        run_directory = (
            self.output_root
            / run_id
        )

        run_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        filename = (
            "instagram_reel_"
            f"{digest}.mp4"
        )

        final_path = (
            run_directory
            / filename
        )

        storage_key = str(
            Path(run_id)
            / filename
        ).replace(
            "\\",
            "/",
        )

        duration_seconds = (
            len(storyboard.scenes)
            * settings
            .reel_scene_duration_seconds
        )

        if not final_path.is_file():

            staging = (
                run_directory
                / (
                    ".reel-"
                    f"{digest}-"
                    f"{uuid4().hex[:8]}"
                )
            )

            staging.mkdir(
                parents=True,
                exist_ok=False,
            )

            try:
                clips = []

                for (
                    index,
                    (
                        scene,
                        source_image,
                    ),
                ) in enumerate(
                    zip(
                        storyboard.scenes,
                        scene_images,
                        strict=True,
                    ),
                    start=1,
                ):
                    card_path = (
                        staging
                        / (
                            "scene_"
                            f"{index:02d}.jpg"
                        )
                    )

                    self._render_scene_card(
                        scene=scene,
                        source_image=(
                            source_image
                        ),
                        output_path=(
                            card_path
                        ),
                    )

                    clip_path = (
                        staging
                        / (
                            "scene_"
                            f"{index:02d}.mp4"
                        )
                    )

                    self._render_scene_clip(
                        card_path=card_path,
                        clip_path=clip_path,
                    )

                    clips.append(
                        clip_path
                    )

                concat_path = (
                    staging
                    / "concat.txt"
                )

                concat_path.write_text(
                    "".join(
                        (
                            "file '"
                            + clip.name.replace(
                                "'",
                                "'\\''",
                            )
                            + "'\n"
                        )
                        for clip
                        in clips
                    ),
                    encoding="utf-8",
                )

                assembled_path = (
                    staging
                    / "assembled.mp4"
                )

                self.command_runner.run(
                    [
                        self.ffmpeg_binary,
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        concat_path.name,
                        "-c",
                        "copy",
                        "-movflags",
                        "+faststart",
                        assembled_path.name,
                    ],
                    cwd=staging,
                )

                if (
                    not assembled_path.is_file()
                    or assembled_path.stat().st_size
                    <= 0
                ):
                    raise RuntimeError(
                        "FFmpeg did not produce "
                        "the final Reel video."
                    )

                assembled_path.replace(
                    final_path
                )

            finally:
                shutil.rmtree(
                    staging,
                    ignore_errors=True,
                )

        if final_path.stat().st_size <= 0:
            raise RuntimeError(
                "Rendered Reel video is empty."
            )

        return GeneratedVideoAsset(
            platform="instagram",
            asset_type="reel_video",
            storyboard_asset_type=(
                storyboard.asset_type
            ),
            storage_key=storage_key,
            provider=self.PROVIDER_NAME,
            model=self.MODEL_NAME,
            width=(
                settings
                .instagram_reel_width
            ),
            height=(
                settings
                .instagram_reel_height
            ),
            fps=settings.reel_fps,
            duration_seconds=(
                duration_seconds
            ),
            scene_count=(
                len(
                    storyboard.scenes
                )
            ),
            source_image_storage_keys=(
                source_keys
            ),
        )

    def _render_scene_card(
        self,
        *,
        scene: StoryboardScene,
        source_image: GeneratedImageAsset,
        output_path: Path,
    ) -> None:

        source_ref = (
            self.source_store.store(
                source_image.storage_key
            )
        )

        source_path = (
            self.source_store
            .resolve_path(
                source_ref
            )
        )

        width = (
            settings
            .instagram_reel_width
        )

        height = (
            settings
            .instagram_reel_height
        )

        with Image.open(
            source_path
        ) as source:

            source = (
                ImageOps
                .exif_transpose(
                    source
                )
                .convert(
                    "RGB"
                )
            )

            background = (
                ImageOps.fit(
                    source,
                    (
                        width,
                        height,
                    ),
                    method=(
                        Image.Resampling
                        .LANCZOS
                    ),
                )
                .filter(
                    ImageFilter
                    .GaussianBlur(
                        radius=28
                    )
                )
            )

            foreground = (
                ImageOps.contain(
                    source,
                    (
                        width,
                        height,
                    ),
                    method=(
                        Image.Resampling
                        .LANCZOS
                    ),
                )
            )

            canvas = (
                background
                .convert(
                    "RGBA"
                )
            )

            shade = Image.new(
                "RGBA",
                (
                    width,
                    height,
                ),
                (
                    0,
                    0,
                    0,
                    70,
                ),
            )

            canvas = (
                Image.alpha_composite(
                    canvas,
                    shade,
                )
            )

            x = (
                width
                - foreground.width
            ) // 2

            y = (
                height
                - foreground.height
            ) // 2

            canvas.alpha_composite(
                foreground.convert(
                    "RGBA"
                ),
                (
                    x,
                    y,
                ),
            )

            overlay = Image.new(
                "RGBA",
                (
                    width,
                    height,
                ),
                (
                    0,
                    0,
                    0,
                    0,
                ),
            )

            draw = ImageDraw.Draw(
                overlay
            )

            text = (
                scene.on_screen_text
                or scene.narration
            ).strip()

            text = text[:220]

            if text:
                font = self._load_font()

                margin = (
                    settings
                    .reel_text_margin
                )

                max_width = (
                    width
                    - 2 * margin
                )

                lines = self._wrap_text(
                    draw=draw,
                    text=text,
                    font=font,
                    max_width=max_width,
                )

                line_gap = 18

                line_heights = []

                for line in lines:
                    bbox = draw.textbbox(
                        (
                            0,
                            0,
                        ),
                        line,
                        font=font,
                    )

                    line_heights.append(
                        bbox[3]
                        - bbox[1]
                    )

                text_height = (
                    sum(
                        line_heights
                    )
                    + line_gap
                    * max(
                        0,
                        len(lines)
                        - 1,
                    )
                )

                panel_padding = 44

                panel_bottom = (
                    height
                    - margin
                )

                panel_top = (
                    panel_bottom
                    - text_height
                    - 2
                    * panel_padding
                )

                draw.rounded_rectangle(
                    (
                        margin,
                        panel_top,
                        width
                        - margin,
                        panel_bottom,
                    ),
                    radius=36,
                    fill=(
                        0,
                        0,
                        0,
                        185,
                    ),
                )

                text_y = (
                    panel_top
                    + panel_padding
                )

                for (
                    line,
                    line_height,
                ) in zip(
                    lines,
                    line_heights,
                    strict=True,
                ):

                    bbox = draw.textbbox(
                        (
                            0,
                            0,
                        ),
                        line,
                        font=font,
                    )

                    line_width = (
                        bbox[2]
                        - bbox[0]
                    )

                    draw.text(
                        (
                            (
                                width
                                - line_width
                            )
                            / 2,
                            text_y,
                        ),
                        line,
                        font=font,
                        fill=(
                            255,
                            255,
                            255,
                            255,
                        ),
                    )

                    text_y += (
                        line_height
                        + line_gap
                    )

            canvas = (
                Image.alpha_composite(
                    canvas,
                    overlay,
                )
                .convert(
                    "RGB"
                )
            )

            canvas.save(
                output_path,
                format="JPEG",
                quality=92,
                optimize=True,
            )

    def _render_scene_clip(
        self,
        *,
        card_path: Path,
        clip_path: Path,
    ) -> None:

        duration = (
            settings
            .reel_scene_duration_seconds
        )

        transition = min(
            settings
            .reel_transition_seconds,
            duration / 3,
        )

        fade_out_start = max(
            0.0,
            duration
            - transition,
        )

        width = (
            settings
            .instagram_reel_width
        )

        height = (
            settings
            .instagram_reel_height
        )

        fps = settings.reel_fps

        video_filter = (
            "zoompan="
            "z='min(zoom+0.0008,1.06)':"
            "d=1:"
            f"s={width}x{height}:"
            f"fps={fps},"
            "fade="
            "t=in:"
            "st=0:"
            f"d={transition:.3f},"
            "fade="
            "t=out:"
            f"st={fade_out_start:.3f}:"
            f"d={transition:.3f}"
        )

        self.command_runner.run(
            [
                self.ffmpeg_binary,
                "-y",
                "-loop",
                "1",
                "-framerate",
                str(
                    fps
                ),
                "-i",
                str(
                    card_path
                ),
                "-vf",
                video_filter,
                "-t",
                f"{duration:.3f}",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                settings
                .reel_video_preset,
                "-crf",
                str(
                    settings
                    .reel_video_crf
                ),
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(
                    fps
                ),
                str(
                    clip_path
                ),
            ]
        )

        if (
            not clip_path.is_file()
            or clip_path.stat().st_size
            <= 0
        ):
            raise RuntimeError(
                "FFmpeg did not produce "
                f"scene clip: {clip_path.name}"
            )

    def _render_digest(
        self,
        *,
        storyboard: VideoStoryboard,
        source_keys: list[str],
    ) -> str:

        payload = {
            "storyboard":
                storyboard.model_dump(
                    mode="json"
                ),
            "source_keys":
                source_keys,
            "provider":
                self.PROVIDER_NAME,
            "model":
                self.MODEL_NAME,
            "width":
                settings
                .instagram_reel_width,
            "height":
                settings
                .instagram_reel_height,
            "scene_duration_seconds":
                settings
                .reel_scene_duration_seconds,
            "fps":
                settings.reel_fps,
            "crf":
                settings
                .reel_video_crf,
            "preset":
                settings
                .reel_video_preset,
            "transition_seconds":
                settings
                .reel_transition_seconds,
        }

        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            ensure_ascii=False,
        ).encode(
            "utf-8"
        )

        return (
            hashlib.sha256(
                encoded
            )
            .hexdigest()[
                :12
            ]
        )

    def _load_font(
        self,
    ):

        font_path = (
            settings
            .reel_text_font_path
        )

        if font_path:
            path = Path(
                font_path
            ).expanduser()

            if not path.is_file():
                raise FileNotFoundError(
                    "Configured Reel font "
                    f"does not exist: {path}"
                )

            return (
                ImageFont
                .truetype(
                    str(path),
                    size=(
                        settings
                        .reel_text_font_size
                    ),
                )
            )

        try:
            return ImageFont.load_default(
                size=(
                    settings
                    .reel_text_font_size
                )
            )

        except TypeError:
            return ImageFont.load_default()

    @staticmethod
    def _wrap_text(
        *,
        draw: ImageDraw.ImageDraw,
        text: str,
        font,
        max_width: int,
    ) -> list[str]:

        words = text.split()

        if not words:
            return []

        lines = []
        current = words[0]

        for word in words[1:]:

            candidate = (
                f"{current} {word}"
            )

            bbox = draw.textbbox(
                (
                    0,
                    0,
                ),
                candidate,
                font=font,
            )

            if (
                bbox[2]
                - bbox[0]
                <= max_width
            ):
                current = candidate

            else:
                lines.append(
                    current
                )
                current = word

        lines.append(
            current
        )

        return lines

    @staticmethod
    def _image_sort_key(
        image: GeneratedImageAsset,
    ) -> tuple:

        match = re.search(
            r"(\d+)$",
            image.asset_type,
        )

        order = (
            int(
                match.group(1)
            )
            if match
            else 10_000
        )

        return (
            order,
            image.asset_type,
            image.storage_key,
        )

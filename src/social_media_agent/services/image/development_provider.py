import hashlib
import io
import textwrap

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
)

from social_media_agent.services.image.base import (
    ImageGenerationResult,
)


class DevelopmentImageProvider:

    PROVIDER_NAME = "development"
    MODEL_NAME = "deterministic-placeholder-v1"

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> ImageGenerationResult:

        if width <= 0 or height <= 0:
            raise ValueError(
                "Image dimensions must be "
                "greater than zero."
            )

        normalized_prompt = (
            " ".join(prompt.split())
            or "Generated social media asset"
        )

        digest = hashlib.sha256(
            normalized_prompt.encode("utf-8")
        ).digest()

        accent = (
            80 + digest[0] % 96,
            80 + digest[1] % 96,
            80 + digest[2] % 96,
        )

        image = Image.new(
            "RGB",
            (width, height),
            (248, 248, 248),
        )

        draw = ImageDraw.Draw(
            image
        )

        header_height = max(
            72,
            int(height * 0.12),
        )

        draw.rectangle(
            (
                0,
                0,
                width,
                header_height,
            ),
            fill=accent,
        )

        margin = max(
            24,
            int(min(width, height) * 0.05),
        )

        font = ImageFont.load_default()

        draw.text(
            (
                margin,
                max(
                    12,
                    header_height // 3,
                ),
            ),
            "DEVELOPMENT PREVIEW",
            fill=(255, 255, 255),
            font=font,
        )

        body_top = (
            header_height
            + margin
        )

        body_width = max(
            20,
            width - (2 * margin),
        )

        estimated_char_width = 7

        chars_per_line = max(
            20,
            body_width
            // estimated_char_width,
        )

        excerpt = normalized_prompt[
            :1200
        ]

        lines = textwrap.wrap(
            excerpt,
            width=chars_per_line,
            break_long_words=False,
            break_on_hyphens=False,
        )

        max_lines = max(
            3,
            int(
                (
                    height
                    - body_top
                    - margin
                    - 60
                )
                / 18
            ),
        )

        visible_lines = lines[
            :max_lines
        ]

        if len(lines) > max_lines:
            visible_lines[-1] = (
                visible_lines[-1]
                .rstrip(" .")
                + "..."
            )

        draw.multiline_text(
            (
                margin,
                body_top,
            ),
            "\n".join(
                visible_lines
            ),
            fill=(30, 30, 30),
            font=font,
            spacing=6,
        )

        footer = (
            f"{width}x{height} | "
            f"{self.MODEL_NAME}"
        )

        draw.text(
            (
                margin,
                height - margin - 16,
            ),
            footer,
            fill=(90, 90, 90),
            font=font,
        )

        output = io.BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=90,
            optimize=True,
        )

        return ImageGenerationResult(
            image_bytes=output.getvalue(),
            width=width,
            height=height,
            provider=self.PROVIDER_NAME,
            model=self.MODEL_NAME,
            file_extension="jpeg",
        )

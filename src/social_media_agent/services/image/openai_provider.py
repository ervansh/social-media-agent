import base64
import binascii
import io
import math
from typing import Any

import requests
from PIL import Image, UnidentifiedImageError

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.base import (
    ImageGenerationResult,
)


class OpenAIImageAPIError(
    RuntimeError
):
    pass


class OpenAIImageProvider:

    PROVIDER_NAME = "openai"

    GENERATION_ENDPOINT = "/images/generations"

    GPT_IMAGE_25_MODELS = {
        "gpt-image-2.5-flare",
        "gpt-image-2.5-flare-2026-09-08",
        "gpt-image-2.5-sunburst",
        "gpt-image-2.5-sunburst-2026-09-08",
    }

    ALLOWED_OUTPUT_FORMATS = {
        "png",
        "jpeg",
        "webp",
    }

    ALLOWED_QUALITY = {
        "auto",
        "low",
        "medium",
        "high",
    }

    GPT_IMAGE_25_QUALITY = (
        ALLOWED_QUALITY
        | {
            "xhigh",
            "max",
        }
    )

    MIN_TOTAL_PIXELS = 655_360
    MAX_TOTAL_PIXELS = 8_294_400
    MAX_EDGE_PIXELS = 3_840
    MAX_ASPECT_RATIO = 3.0

    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):

        self.api_key = (
            api_key
            if api_key is not None
            else settings.openai_api_key
        )

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required "
                "when IMAGE_PROVIDER=openai."
            )

        self.base_url = (
            base_url
            if base_url is not None
            else settings.openai_image_base_url
        ).rstrip("/")

        self.model = (
            model
            if model is not None
            else settings.openai_image_model
        )

        self.session = (
            session
            or requests.Session()
        )

        self.output_format = (
            settings
            .openai_image_output_format
            .strip()
            .lower()
        )

        if self.output_format == "jpg":
            self.output_format = "jpeg"

        self.quality = (
            settings
            .openai_image_quality
            .strip()
            .lower()
        )

        self.background = (
            settings
            .openai_image_background
            .strip()
            .lower()
        )

        self.output_compression = (
            settings
            .openai_image_output_compression
        )

        self._validate_configuration()

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> ImageGenerationResult:

        if not prompt or not prompt.strip():
            raise ValueError(
                "Image generation prompt "
                "cannot be empty."
            )

        (
            normalized_width,
            normalized_height,
        ) = self._normalize_size(
            width,
            height,
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt.strip(),
            "size": (
                f"{normalized_width}"
                f"x{normalized_height}"
            ),
            "quality": self.quality,
            "output_format":
                self.output_format,
            "background":
                self.background,
            "n": 1,
        }

        if (
            self.output_format
            in {
                "jpeg",
                "webp",
            }
        ):
            payload[
                "output_compression"
            ] = self.output_compression

        response_data = self._request(
            payload
        )

        data = response_data.get(
            "data"
        )

        if (
            not isinstance(data, list)
            or not data
            or not isinstance(
                data[0],
                dict,
            )
        ):
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "no image data."
            )

        encoded_image = data[0].get(
            "b64_json"
        )

        if not encoded_image:
            raise OpenAIImageAPIError(
                "OpenAI Images API response "
                "did not contain b64_json."
            )

        try:
            image_bytes = (
                base64.b64decode(
                    encoded_image,
                    validate=True,
                )
            )

        except (
            binascii.Error,
            ValueError,
        ) as exc:
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "invalid base64 image data."
            ) from exc

        (
            actual_width,
            actual_height,
            detected_format,
        ) = self._inspect_image(
            image_bytes
        )

        expected_format = (
            "JPEG"
            if self.output_format == "jpeg"
            else self.output_format.upper()
        )

        if (
            detected_format
            != expected_format
        ):
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "an unexpected image format. "
                f"Requested={expected_format}, "
                f"received={detected_format}."
            )

        return ImageGenerationResult(
            image_bytes=image_bytes,
            width=actual_width,
            height=actual_height,
            provider="openai",
            model=self.model,
            file_extension=(
                self.output_format
            ),
        )

    def _request(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        try:
            response = (
                self.session.post(
                    (
                        f"{self.base_url}"
                        f"{self.GENERATION_ENDPOINT}"
                    ),
                    headers={
                        "Authorization": (
                            f"Bearer "
                            f"{self.api_key}"
                        ),
                        "Content-Type":
                            "application/json",
                    },
                    json=payload,
                    timeout=(
                        settings
                        .image_generation_timeout_seconds
                    ),
                )
            )

        except requests.RequestException as exc:
            raise OpenAIImageAPIError(
                "OpenAI Images API request failed."
            ) from exc

        try:
            response_data = response.json()

        except ValueError as exc:
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "a non-JSON response."
            ) from exc

        if not response.ok:

            error = response_data.get(
                "error",
                {},
            )

            if isinstance(
                error,
                dict,
            ):
                message = error.get(
                    "message",
                    "Unknown OpenAI image error.",
                )

                error_type = error.get(
                    "type",
                    "unknown",
                )

                error_code = error.get(
                    "code",
                    "unknown",
                )

            else:
                message = str(
                    error
                )
                error_type = "unknown"
                error_code = "unknown"

            raise OpenAIImageAPIError(
                "OpenAI Images API request "
                "failed. "
                f"status={response.status_code}, "
                f"type={error_type}, "
                f"code={error_code}, "
                f"message={message}"
            )

        if not isinstance(
            response_data,
            dict,
        ):
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "an unexpected response shape."
            )

        return response_data

    def _normalize_size(
        self,
        width: int,
        height: int,
    ) -> tuple[int, int]:

        if width <= 0 or height <= 0:
            raise ValueError(
                "Image dimensions must be "
                "greater than zero."
            )

        multiple = (
            settings.image_size_multiple
        )

        if multiple <= 0:
            raise ValueError(
                "IMAGE_SIZE_MULTIPLE must "
                "be greater than zero."
            )

        normalized_width = int(
            math.ceil(
                width / multiple
            )
            * multiple
        )

        normalized_height = int(
            math.ceil(
                height / multiple
            )
            * multiple
        )

        self._validate_dimensions(
            normalized_width,
            normalized_height,
        )

        return (
            normalized_width,
            normalized_height,
        )

    def _validate_dimensions(
        self,
        width: int,
        height: int,
    ) -> None:

        if (
            width > self.MAX_EDGE_PIXELS
            or height
            > self.MAX_EDGE_PIXELS
        ):
            raise ValueError(
                "OpenAI GPT Image dimensions "
                "cannot exceed 3840 pixels "
                "on either edge."
            )

        longer = max(
            width,
            height,
        )

        shorter = min(
            width,
            height,
        )

        if (
            longer / shorter
            > self.MAX_ASPECT_RATIO
        ):
            raise ValueError(
                "OpenAI GPT Image aspect ratio "
                "cannot exceed 3:1."
            )

        total_pixels = (
            width
            * height
        )

        if (
            total_pixels
            < self.MIN_TOTAL_PIXELS
            or total_pixels
            > self.MAX_TOTAL_PIXELS
        ):
            raise ValueError(
                "OpenAI GPT Image total pixel "
                "count must be between "
                "655360 and 8294400."
            )

    def _validate_configuration(
        self,
    ) -> None:

        if (
            self.output_format
            not in self.ALLOWED_OUTPUT_FORMATS
        ):
            raise ValueError(
                "OPENAI_IMAGE_OUTPUT_FORMAT must "
                "be png, jpeg, or webp."
            )

        allowed_quality = (
            self.GPT_IMAGE_25_QUALITY
            if self.model
            in self.GPT_IMAGE_25_MODELS
            else self.ALLOWED_QUALITY
        )

        if (
            self.quality
            not in allowed_quality
        ):
            raise ValueError(
                "Unsupported OpenAI image quality "
                f"'{self.quality}' for model "
                f"'{self.model}'."
            )

        if self.background not in {
            "auto",
            "opaque",
            "transparent",
        }:
            raise ValueError(
                "OPENAI_IMAGE_BACKGROUND must be "
                "auto, opaque, or transparent."
            )

        if (
            self.background
            == "transparent"
            and self.output_format
            == "jpeg"
        ):
            raise ValueError(
                "Transparent OpenAI image "
                "background requires PNG or WebP."
            )

        if not (
            0
            <= self.output_compression
            <= 100
        ):
            raise ValueError(
                "OPENAI_IMAGE_OUTPUT_COMPRESSION "
                "must be between 0 and 100."
            )

    @staticmethod
    def _inspect_image(
        image_bytes: bytes,
    ) -> tuple[int, int, str]:

        if not image_bytes:
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "empty image bytes."
            )

        try:
            with Image.open(
                io.BytesIO(
                    image_bytes
                )
            ) as image:

                image.load()

                width, height = (
                    image.size
                )

                detected_format = (
                    image.format
                )

        except (
            UnidentifiedImageError,
            OSError,
        ) as exc:
            raise OpenAIImageAPIError(
                "OpenAI Images API returned "
                "invalid image bytes."
            ) from exc

        if not detected_format:
            raise OpenAIImageAPIError(
                "Generated image format "
                "could not be detected."
            )

        return (
            width,
            height,
            detected_format.upper(),
        )

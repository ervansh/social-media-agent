import base64
import math

import requests

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.image.base import (
    ImageGenerationResult,
)


class OpenAIImageProvider:

    GENERATION_ENDPOINT = "/images/generations"

    def __init__(self):

        if not settings.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY is required " "when IMAGE_PROVIDER=openai."
            )

        self.base_url = settings.openai_image_base_url.rstrip("/")

        self.api_key = settings.openai_api_key

        self.model = settings.openai_image_model

    def _normalize_dimension(
        self,
        value: int,
    ) -> int:

        multiple = settings.image_size_multiple

        return int(math.ceil(value / multiple) * multiple)

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> ImageGenerationResult:

        normalized_width = self._normalize_dimension(width)

        normalized_height = self._normalize_dimension(height)

        size = f"{normalized_width}" f"x{normalized_height}"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "quality": (settings.openai_image_quality),
            "output_format": (settings.openai_image_output_format),
            "n": 1,
        }

        response = requests.post(
            (f"{self.base_url}" f"{self.GENERATION_ENDPOINT}"),
            headers={
                "Authorization": (f"Bearer {self.api_key}"),
                "Content-Type": ("application/json"),
            },
            json=payload,
            timeout=(settings.image_generation_timeout_seconds),
        )

        response.raise_for_status()

        response_data = response.json()

        if "data" not in response_data or not response_data["data"]:
            raise RuntimeError("Image provider returned " "no image data.")

        encoded_image = response_data["data"][0].get("b64_json")

        if not encoded_image:
            raise RuntimeError("Image provider response " "did not contain b64_json.")

        image_bytes = base64.b64decode(encoded_image)

        return ImageGenerationResult(
            image_bytes=image_bytes,
            width=normalized_width,
            height=normalized_height,
            provider="openai",
            model=self.model,
            file_extension=(settings.openai_image_output_format),
        )

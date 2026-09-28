from social_media_agent.services.image.base import (
    ImageGenerationResult,
)


class DisabledImageProvider:

    PROVIDER_NAME = "disabled"

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
        negative_prompt: str | None = None,
    ) -> ImageGenerationResult:

        raise RuntimeError(
            "Image generation is disabled."
        )
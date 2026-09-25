import re
from pathlib import Path
from uuid import uuid4

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
    GeneratedImageAsset,
)
from social_media_agent.services.image.base import (
    ImageProvider,
)


class CreativeImageGenerationService:

    def __init__(
        self,
        provider: ImageProvider,
        output_root: str | Path | None = None,
    ):
        self.provider = provider

        self.output_root = Path(output_root or settings.generated_assets_dir)

    @property
    def provider_name(
        self,
    ) -> str:

        provider_name = getattr(
            self.provider,
            "PROVIDER_NAME",
            None,
        )

        if not provider_name:
            raise RuntimeError(
                "Image provider must expose "
                "PROVIDER_NAME."
            )

        return str(
            provider_name
        )

    def generate(
        self,
        run_id: str,
        creative_assets: CreativeAssetBundle,
    ) -> GeneratedAssetBundle:

        generated_images: list[GeneratedImageAsset] = []

        run_directory = self.output_root / run_id

        run_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for brief in creative_assets.images:

            prompt_parts = [
                brief.image_prompt.strip()
            ]

            if brief.text_overlay:
                prompt_parts.append(
                    "Render the following text "
                    "exactly once, clearly and "
                    "legibly: "
                    f'\"{brief.text_overlay.strip()}\"'
                )

            if brief.negative_prompt:
                prompt_parts.append(
                    "Avoid the following: "
                    f"{brief.negative_prompt.strip()}"
                )

            prompt = "\n\n".join(
                prompt_parts
            )

            result = self.provider.generate(
                prompt=prompt,
                width=brief.width,
                height=brief.height,
            )

            asset_type = self._safe_name(brief.asset_type)

            filename = (
                f"{brief.platform}_"
                f"{asset_type}_"
                f"{uuid4().hex[:12]}"
                f".{result.file_extension}"
            )

            file_path = run_directory / filename

            file_path.write_bytes(result.image_bytes)

            storage_key = str(Path(run_id) / filename)

            generated_images.append(
                GeneratedImageAsset(
                    platform=brief.platform,
                    asset_type=brief.asset_type,
                    storage_key=storage_key,
                    provider=result.provider,
                    model=result.model,
                    requested_width=brief.width,
                    requested_height=brief.height,
                    generated_width=result.width,
                    generated_height=result.height,
                    prompt=prompt,
                )
            )

        return GeneratedAssetBundle(images=generated_images)

    @staticmethod
    def _safe_name(
        value: str,
    ) -> str:

        normalized = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            value.strip().lower(),
        )

        return normalized.strip("_")

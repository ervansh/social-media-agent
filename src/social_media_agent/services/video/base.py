from typing import Protocol

from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)


class VideoRenderer(Protocol):

    PROVIDER_NAME: str
    MODEL_NAME: str

    @property
    def provider_name(
        self,
    ) -> str:
        ...

    def verify_available(
        self,
    ) -> None:
        ...

    def render(
        self,
        *,
        run_id: str,
        creative_assets: CreativeAssetBundle,
        generated_assets: GeneratedAssetBundle,
    ) -> GeneratedAssetBundle:
        ...

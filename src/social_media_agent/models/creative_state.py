from typing import TypedDict

from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)


class CreativeState(
    TypedDict,
    total=False,
):
    strategy: ContentStrategy
    master_content: MasterContent

    youtube: YouTubePackage
    instagram: InstagramPackage
    x: XPackage

    creative_assets: CreativeAssetBundle
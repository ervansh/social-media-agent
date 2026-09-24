from typing import TypedDict

from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.quality import (
    QualityReport,
)


class QualityState(
    TypedDict,
    total=False,
):
    strategy: ContentStrategy
    master_content: MasterContent

    youtube: YouTubePackage
    instagram: InstagramPackage
    x: XPackage

    quality_report: QualityReport

    retry_count: int
    quality_status: str
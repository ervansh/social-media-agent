from typing import TypedDict

from social_media_agent.models.content_idea import (
    ContentIdea,
)
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.grounding import (
    GroundingReport,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.research import (
    ResearchBrief,
)


class ContentCreationState(
    TypedDict,
    total=False,
):
    research: ResearchBrief
    selected_idea: ContentIdea

    strategy: ContentStrategy
    master_content: MasterContent

    grounding_report: GroundingReport
    grounding_retry_count: int
    grounding_status: str

    review_status: str
from typing import TypedDict

from social_media_agent.models.content_idea import IdeaBatch
from social_media_agent.models.research import ResearchBrief


class IdeationState(TypedDict, total=False):

    topic: str
    audience: str

    research: ResearchBrief
    ideas: IdeaBatch

    approval_status: str
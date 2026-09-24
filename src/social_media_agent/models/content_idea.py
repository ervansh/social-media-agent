from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal["youtube", "instagram", "x"]


class ContentIdea(BaseModel):
    title: str
    hook: str
    angle: str
    target_audience: str
    recommended_platforms: list[Platform]
    rationale: str


class IdeaBatch(BaseModel):
    ideas: list[ContentIdea] = Field(min_length=1)
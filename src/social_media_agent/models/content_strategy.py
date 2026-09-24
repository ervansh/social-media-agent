from typing import Literal

from pydantic import BaseModel, Field


ContentDepth = Literal["short", "medium", "deep"]


class ContentStrategy(BaseModel):
    objective: str
    core_message: str
    tone: str
    content_depth: ContentDepth

    story_structure: list[str] = Field(min_length=2)
    must_include_points: list[str] = Field(min_length=1)

    avoid_claims: list[str] = Field(default_factory=list)

    call_to_action: str
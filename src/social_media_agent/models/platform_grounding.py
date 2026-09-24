from typing import Literal

from pydantic import BaseModel, Field

from social_media_agent.models.grounding import (
    GroundingIssue,
)


PlatformName = Literal[
    "youtube",
    "instagram",
    "x",
]


class SemanticPlatformGroundingReview(BaseModel):
    summary: str

    issues: list[GroundingIssue] = Field(
        default_factory=list
    )


class PlatformGroundingReport(BaseModel):
    platform: PlatformName

    passed: bool

    summary: str

    issues: list[GroundingIssue] = Field(
        default_factory=list
    )


class PlatformGroundingBatch(BaseModel):
    passed: bool

    reports: list[
        PlatformGroundingReport
    ] = Field(
        default_factory=list
    )
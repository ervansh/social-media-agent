from typing import Literal

from pydantic import BaseModel, Field


class GroundingIssue(BaseModel):
    severity: Literal[
        "supported",
        "warning",
        "error",
    ]

    claim: str
    reason: str

    supporting_source_urls: list[str] = Field(
        default_factory=list
    )


class SemanticGroundingReview(BaseModel):
    summary: str

    issues: list[GroundingIssue] = Field(
        default_factory=list
    )


class GroundingReport(BaseModel):
    review_version: int = 1
    passed: bool
    summary: str

    issues: list[GroundingIssue] = Field(
        default_factory=list
    )
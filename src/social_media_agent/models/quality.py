from typing import Literal

from pydantic import BaseModel, Field


QualityPlatform = Literal[
    "youtube",
    "instagram",
    "x",
    "general",
]

Severity = Literal[
    "error",
    "warning",
]


class QualityIssue(BaseModel):
    platform: QualityPlatform
    severity: Severity

    field: str | None = None
    message: str


class SemanticQualityReview(BaseModel):
    summary: str

    issues: list[QualityIssue] = Field(
        default_factory=list
    )


class QualityReport(BaseModel):
    passed: bool
    summary: str

    issues: list[QualityIssue] = Field(
        default_factory=list
    )
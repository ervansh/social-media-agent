from typing import Literal

from pydantic import BaseModel, Field


Platform = Literal[
    "youtube",
    "instagram",
    "x",
]

PublicationStatus = Literal[
    "ready",
    "blocked",
    "dry_run",
    "published",
    "failed",
]


class PublicationRequest(BaseModel):
    run_id: str
    platform: Platform

    publication_plan_id: str | None = None
    content_artifact_version: int | None = None
    generated_assets_version: int | None = None

    payload: dict

    media_storage_keys: list[str] = Field(
        default_factory=list
    )


class PublicationResult(BaseModel):
    platform: Platform
    status: PublicationStatus

    message: str

    external_id: str | None = None

    response_payload: dict = Field(
        default_factory=dict
    )


class PublicationBatch(BaseModel):
    publication_plan_id: str | None = None

    results: list[PublicationResult] = Field(
        default_factory=list
    )
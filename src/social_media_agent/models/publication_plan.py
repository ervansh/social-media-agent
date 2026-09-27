from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class ArtifactVersionRef(BaseModel):
    artifact_id: str
    artifact_type: str
    platform: str | None = None
    version: int


class PublicationPlan(BaseModel):
    plan_id: str = Field(
        default_factory=lambda: str(
            uuid4()
        )
    )

    run_id: str

    platforms: list[str] = Field(
        min_length=1
    )

    artifact_refs: list[
        ArtifactVersionRef
    ] = Field(
        min_length=1
    )

    created_at: datetime = Field(
        default_factory=lambda: (
            datetime.now(
                timezone.utc
            )
        )
    )

    def get_ref(
        self,
        *,
        artifact_type: str,
        platform: str | None = None,
    ) -> ArtifactVersionRef | None:

        for ref in self.artifact_refs:

            if (
                ref.artifact_type
                == artifact_type
                and ref.platform
                == platform
            ):
                return ref

        return None

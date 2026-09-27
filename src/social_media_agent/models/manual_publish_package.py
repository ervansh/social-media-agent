from datetime import datetime, timezone

from pydantic import BaseModel, Field

from social_media_agent.models.publication_plan import (
    ArtifactVersionRef,
)
from social_media_agent.models.stored_media import (
    StoredMediaAsset,
)


class ManualPublishFile(BaseModel):
    relative_path: str
    platform: str | None = None
    role: str

    content_type: str
    size_bytes: int
    sha256: str

    source_provider: str | None = None
    source_model: str | None = None

    stored_media: StoredMediaAsset


class ManualPublishPackage(BaseModel):
    schema_version: int = 1

    run_id: str
    publication_plan_id: str

    store_provider: str
    package_key: str

    platforms: list[str] = Field(
        min_length=1
    )

    artifact_refs: list[
        ArtifactVersionRef
    ] = Field(
        min_length=1
    )

    files: list[
        ManualPublishFile
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

    @property
    def manifest_file(
        self,
    ) -> ManualPublishFile | None:

        for file in self.files:
            if file.role == "manifest":
                return file

        return None

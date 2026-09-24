from pydantic import BaseModel

from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.repository import (
    ContentRepository,
)


class PersistenceService:

    def __init__(
        self,
        repository: ContentRepository,
    ):
        self.repository = repository

    def start_run(
        self,
        topic: str,
        audience: str,
    ) -> str:

        run = self.repository.create_run(
            topic=topic,
            audience=audience,
            status="researching",
        )

        return run.id

    def update_status(
        self,
        run_id: str,
        status: str,
    ) -> None:

        self.repository.update_run_status(
            run_id,
            status,
        )

    def save_model(
        self,
        run_id: str,
        artifact_type: ArtifactType,
        model: BaseModel,
        platform: str | None = None,
    ) -> None:

        self.repository.save_artifact(
            run_id=run_id,
            artifact_type=artifact_type.value,
            platform=platform,
            payload=model.model_dump(mode="json"),
        )

    def save_payload(
        self,
        run_id: str,
        artifact_type: ArtifactType | str,
        payload: dict,
        platform: str | None = None,
    ) -> None:

        artifact_name = (
            artifact_type.value
            if isinstance(
                artifact_type,
                ArtifactType,
            )
            else artifact_type
        )

        self.repository.save_artifact(
            run_id=run_id,
            artifact_type=artifact_name,
            platform=platform,
            payload=payload,
        )

    def get_run(
        self,
        run_id: str,
    ):
        return self.repository.get_run(run_id)

    def list_runs(
        self,
        limit: int = 50,
    ):
        return self.repository.list_runs(limit=limit)

    def list_artifacts(
        self,
        run_id: str,
    ):
        return self.repository.list_artifacts(run_id)

    def get_latest_artifacts(
        self,
        run_id: str,
    ):
        artifacts = self.list_artifacts(run_id)

        latest = {}

        for artifact in artifacts:

            key = (
                artifact.artifact_type,
                artifact.platform,
            )

            existing = latest.get(key)

            if existing is None or artifact.version > existing.version:
                latest[key] = artifact

        return list(latest.values())

    def get_latest_payload(
        self,
        run_id: str,
        artifact_type: ArtifactType,
        platform: str | None = None,
    ) -> dict | None:

        artifact = self.repository.get_latest_artifact(
            run_id=run_id,
            artifact_type=artifact_type.value,
            platform=platform,
        )

        if artifact is None:
            return None

        return artifact.payload

    def get_run(
        self,
        run_id: str,
    ):
        return self.repository.get_run(run_id)

    def list_runs(
        self,
        limit: int = 50,
    ):
        return self.repository.list_runs(limit=limit)

    def list_artifacts(
        self,
        run_id: str,
    ):
        return self.repository.list_artifacts(run_id)

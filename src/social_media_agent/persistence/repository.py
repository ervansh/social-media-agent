from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import sessionmaker

from social_media_agent.persistence.models import (
    ArtifactRecord,
    ContentRunRecord,
)


class ContentRepository:

    def __init__(
        self,
        session_factory: sessionmaker,
    ):
        self.session_factory = session_factory

    def create_run(
        self,
        topic: str,
        audience: str,
        status: str = "created",
    ) -> ContentRunRecord:

        with self.session_factory.begin() as session:

            run = ContentRunRecord(
                topic=topic,
                audience=audience,
                status=status,
            )

            session.add(run)
            session.flush()

            return run

    def update_run_status(
        self,
        run_id: str,
        status: str,
    ) -> None:

        with self.session_factory.begin() as session:

            run = session.get(
                ContentRunRecord,
                run_id,
            )

            if run is None:
                raise ValueError(
                    f"Content run not found: {run_id}"
                )

            run.status = status

    def save_artifact(
        self,
        run_id: str,
        artifact_type: str,
        payload: dict,
        platform: str | None = None,
    ) -> ArtifactRecord:

        with self.session_factory.begin() as session:

            run_exists = session.get(
                ContentRunRecord,
                run_id,
            )

            if run_exists is None:
                raise ValueError(
                    f"Content run not found: {run_id}"
                )

            version_query = select(
                func.max(
                    ArtifactRecord.version
                )
            ).where(
                ArtifactRecord.run_id == run_id,
                ArtifactRecord.artifact_type
                == artifact_type,
                ArtifactRecord.platform
                == platform,
            )

            latest_version = session.scalar(
                version_query
            )

            artifact = ArtifactRecord(
                run_id=run_id,
                artifact_type=artifact_type,
                platform=platform,
                version=(
                    latest_version or 0
                )
                + 1,
                payload=payload,
            )

            session.add(artifact)
            session.flush()

            return artifact

    def get_latest_artifact(
        self,
        run_id: str,
        artifact_type: str,
        platform: str | None = None,
    ) -> ArtifactRecord | None:

        with self.session_factory() as session:

            query = (
                select(ArtifactRecord)
                .where(
                    ArtifactRecord.run_id
                    == run_id,
                    ArtifactRecord.artifact_type
                    == artifact_type,
                    ArtifactRecord.platform
                    == platform,
                )
                .order_by(
                    ArtifactRecord.version.desc()
                )
                .limit(1)
            )

            return session.scalar(query)

    def get_run(
        self,
        run_id: str,
    ) -> ContentRunRecord | None:

        with self.session_factory() as session:
            return session.get(
                ContentRunRecord,
                run_id,
            )

    def list_runs(
        self,
        limit: int = 50,
    ) -> list[ContentRunRecord]:

        with self.session_factory() as session:

            query = (
                select(ContentRunRecord)
                .order_by(
                    ContentRunRecord.created_at.desc()
                )
                .limit(limit)
            )

            return list(
                session.scalars(query)
            )


    def list_artifacts(
        self,
        run_id: str,
    ) -> list[ArtifactRecord]:

        with self.session_factory() as session:

            query = (
                select(ArtifactRecord)
                .where(
                    ArtifactRecord.run_id == run_id
                )
                .order_by(
                    ArtifactRecord.created_at.desc(),
                    ArtifactRecord.version.desc(),
                )
            )

            return list(
                session.scalars(query)
            )
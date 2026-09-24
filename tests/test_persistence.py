from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from social_media_agent.persistence.database import Base
from social_media_agent.persistence.repository import (
    ContentRepository,
)


def test_content_repository(tmp_path):

    db_path = tmp_path / "test.db"

    engine = create_engine(
        f"sqlite:///{db_path}"
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    repository = ContentRepository(
        session_factory
    )

    run = repository.create_run(
        topic="AI automation testing",
        audience="QA engineers",
    )

    assert run.id is not None

    repository.save_artifact(
        run_id=run.id,
        artifact_type="research",
        payload={
            "summary": "Research test",
        },
    )

    artifact_v1 = (
        repository.get_latest_artifact(
            run_id=run.id,
            artifact_type="research",
        )
    )

    assert artifact_v1 is not None
    assert artifact_v1.version == 1

    repository.save_artifact(
        run_id=run.id,
        artifact_type="research",
        payload={
            "summary": "Updated research",
        },
    )

    artifact_v2 = (
        repository.get_latest_artifact(
            run_id=run.id,
            artifact_type="research",
        )
    )

    assert artifact_v2 is not None
    assert artifact_v2.version == 2

    assert (
        artifact_v2.payload["summary"]
        == "Updated research"
    )

    repository.update_run_status(
        run.id,
        "ready_for_human_review",
    )

    stored_run = repository.get_run(
        run.id
    )

    assert stored_run is not None

    assert (
        stored_run.status
        == "ready_for_human_review"
    )
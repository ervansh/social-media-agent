from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pytest

from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.database import (
    Base,
)
from social_media_agent.persistence.repository import (
    ContentRepository,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.persistence.service import (
    PersistenceService,
)
from social_media_agent.services.review_service import (
    ReviewService,
)


def build_persistence(
    tmp_path,
):

    db_path = (
        tmp_path
        / "publication-plan.db"
    )

    engine = create_engine(
        f"sqlite:///{db_path}"
    )

    Base.metadata.create_all(
        engine
    )

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    return PersistenceService(
        ContentRepository(
            session_factory
        )
    )


def seed_reviewable_x_run(
    persistence,
):

    run_id = persistence.start_run(
        topic="AI testing",
        audience="QA engineers",
    )

    persistence.save_payload(
        run_id,
        ArtifactType.RESEARCH,
        {
            "summary":
                "Grounded research"
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.SELECTED_IDEA,
        {
            "title":
                "AI testing"
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.STRATEGY,
        {
            "tone":
                "practical"
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.MASTER_CONTENT,
        {
            "title":
                "AI Testing Review"
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.GROUNDING_REPORT,
        {
            "passed": True,
            "summary":
                "Grounded",
            "issues": [],
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.PLATFORM_CONTENT,
        {
            "single_post":
                "Approved X content.",
            "thread": [],
            "call_to_action":
                "Review the points.",
        },
        platform="x",
    )

    persistence.save_payload(
        run_id,
        ArtifactType.PLATFORM_GROUNDING_REPORT,
        {
            "passed": True,
            "reports": [],
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.QUALITY_REPORT,
        {
            "passed": True,
            "summary":
                "Quality passed",
            "issues": [],
        },
    )

    persistence.save_payload(
        run_id,
        ArtifactType.CREATIVE_ASSETS,
        {
            "images": [],
            "storyboards": [],
        },
    )

    persistence.update_status(
        run_id,
        RunStatus
        .READY_FOR_HUMAN_REVIEW
        .value,
    )

    return run_id


def test_approval_creates_version_locked_publication_plan(
    tmp_path,
):

    persistence = build_persistence(
        tmp_path
    )

    run_id = (
        seed_reviewable_x_run(
            persistence
        )
    )

    plan = ReviewService(
        persistence=persistence
    ).approve(
        run_id=run_id,
        note="Approved",
    )

    run = persistence.get_run(
        run_id
    )

    assert (
        run.status
        == RunStatus
        .APPROVED_FOR_PUBLISHING
        .value
    )

    assert plan.run_id == run_id
    assert plan.platforms == ["x"]

    x_ref = plan.get_ref(
        artifact_type=(
            ArtifactType
            .PLATFORM_CONTENT
            .value
        ),
        platform="x",
    )

    assert x_ref is not None
    assert x_ref.version == 1

    stored_plan = (
        persistence
        .get_latest_payload(
            run_id,
            ArtifactType.PUBLICATION_PLAN,
        )
    )

    assert (
        stored_plan["plan_id"]
        == plan.plan_id
    )

    review = (
        persistence
        .get_latest_payload(
            run_id,
            ArtifactType.REVIEW_DECISION,
        )
    )

    assert (
        review[
            "publication_plan_id"
        ]
        == plan.plan_id
    )


def test_reviewed_artifact_change_invalidates_approval(
    tmp_path,
):

    persistence = build_persistence(
        tmp_path
    )

    run_id = (
        seed_reviewable_x_run(
            persistence
        )
    )

    ReviewService(
        persistence=persistence
    ).approve(
        run_id=run_id
    )

    persistence.save_payload(
        run_id,
        ArtifactType.PLATFORM_CONTENT,
        {
            "single_post":
                "Changed after approval.",
            "thread": [],
            "call_to_action":
                "Review again.",
        },
        platform="x",
    )

    run = persistence.get_run(
        run_id
    )

    assert (
        run.status
        == RunStatus
        .REQUIRES_REVIEW
        .value
    )


def test_approval_rejects_failed_quality(
    tmp_path,
):

    persistence = build_persistence(
        tmp_path
    )

    run_id = (
        seed_reviewable_x_run(
            persistence
        )
    )

    persistence.save_payload(
        run_id,
        ArtifactType.QUALITY_REPORT,
        {
            "passed": False,
            "summary":
                "Failed",
            "issues": [],
        },
    )

    persistence.update_status(
        run_id,
        RunStatus
        .READY_FOR_HUMAN_REVIEW
        .value,
    )

    with pytest.raises(
        ValueError,
        match="passing quality_report",
    ):
        ReviewService(
            persistence=persistence
        ).approve(
            run_id=run_id
        )

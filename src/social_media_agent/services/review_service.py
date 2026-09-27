from social_media_agent.models.review_decision import (
    ReviewDecision,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.services.publishing.publication_plan_service import (
    PublicationPlanService,
)


class ReviewService:

    def __init__(
        self,
        *,
        persistence,
    ):
        self.persistence = persistence

        self.plan_service = (
            PublicationPlanService(
                persistence=persistence
            )
        )

    def approve(
        self,
        *,
        run_id: str,
        note: str = "",
    ):

        plan = (
            self.plan_service
            .create_for_run(
                run_id
            )
        )

        decision = ReviewDecision(
            decision="approved",
            note=note,
            publication_plan_id=(
                plan.plan_id
            ),
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.REVIEW_DECISION,
            decision,
        )

        self.persistence.update_status(
            run_id,
            RunStatus
            .APPROVED_FOR_PUBLISHING
            .value,
        )

        return plan

    def reject(
        self,
        *,
        run_id: str,
        note: str = "",
    ) -> ReviewDecision:

        decision = ReviewDecision(
            decision="rejected",
            note=note,
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.REVIEW_DECISION,
            decision,
        )

        self.persistence.update_status(
            run_id,
            RunStatus.REJECTED.value,
        )

        return decision

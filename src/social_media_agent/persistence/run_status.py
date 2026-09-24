from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RESEARCHING = "researching"

    AWAITING_IDEA_APPROVAL = "awaiting_idea_approval"
    IDEA_APPROVED = "idea_approved"

    MASTER_CONTENT_READY = "master_content_ready"
    PLATFORM_CONTENT_GENERATED = "platform_content_generated"

    READY_FOR_HUMAN_REVIEW = "ready_for_human_review"

    APPROVED_FOR_PUBLISHING = "approved_for_publishing"
    PUBLISHED = "published"
    REJECTED = "rejected"

    FAILED_GROUNDING = "failed_grounding"
    FAILED_QUALITY_GATE = "failed_quality_gate"

    FAILED_PLATFORM_GROUNDING = (
    "failed_platform_grounding"
)
from enum import StrEnum


class ArtifactType(StrEnum):
    RESEARCH = "research"
    IDEAS = "ideas"
    SELECTED_IDEA = "selected_idea"
    STRATEGY = "strategy"
    MASTER_CONTENT = "master_content"
    GROUNDING_REPORT = "grounding_report"

    PLATFORM_CONTENT = "platform_content"

    PLATFORM_GROUNDING_REPORT = (
        "platform_grounding_report"
    )

    QUALITY_REPORT = "quality_report"
    CREATIVE_ASSETS = "creative_assets"
    GENERATED_ASSETS = "generated_assets"
    REVIEW_DECISION = "review_decision"
    PUBLICATION_RESULT = "publication_result"

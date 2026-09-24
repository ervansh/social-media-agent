from social_media_agent.config.settings import settings
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.quality import (
    QualityReport,
    SemanticQualityReview,
)
from social_media_agent.services.llm.base import (
    LLMProvider,
)
from social_media_agent.services.quality.platform_validator import (
    PlatformValidator,
)


class QualityReviewAgent:

    def __init__(
        self,
        llm: LLMProvider,
        validator: PlatformValidator,
    ):
        self.llm = llm
        self.validator = validator

    def run(
        self,
        strategy: ContentStrategy,
        master_content: MasterContent,
        youtube: YouTubePackage | None = None,
        instagram: InstagramPackage | None = None,
        x: XPackage | None = None,
    ) -> QualityReport:

        # At least one platform must have generated content.
        if youtube is None and instagram is None and x is None:
            raise ValueError(
                "Quality review requires at least " "one generated platform package."
            )

        # ---------------------------------------------
        # Deterministic validation
        # ---------------------------------------------

        deterministic_issues = self.validator.validate(
            youtube=youtube,
            instagram=instagram,
            x=x,
        )

        # ---------------------------------------------
        # Build only generated platform content
        # ---------------------------------------------

        platform_content: list[str] = []

        if youtube is not None:
            platform_content.append("YOUTUBE:\n" + youtube.model_dump_json(indent=2))

        if instagram is not None:
            platform_content.append(
                "INSTAGRAM:\n" + instagram.model_dump_json(indent=2)
            )

        if x is not None:
            platform_content.append("X:\n" + x.model_dump_json(indent=2))

        platform_content_text = "\n\n".join(platform_content)

        # ---------------------------------------------
        # Semantic quality review
        # ---------------------------------------------

        prompt = f"""
You are the quality-control agent for a
social media content generation system.

Review ONLY the platform content supplied below.

The MASTER CONTENT is the canonical source
for this stage of the workflow.

Do not expect content for platforms that are
not included in GENERATED PLATFORM CONTENT.

Check for:

- factual claims not supported by master content
- contradictions with master content
- missing or distorted core message
- misleading wording
- poor adaptation to the target platform
- duplicated or incoherent content
- excessive generic AI-style language
- content that does not follow the strategy

Do NOT introduce new facts.

Use ERROR only when the content should be
regenerated.

Use WARNING for improvements that do not
require regeneration.

CONTENT STRATEGY:

{strategy.model_dump_json(indent=2)}

MASTER CONTENT:

{master_content.model_dump_json(indent=2)}

GENERATED PLATFORM CONTENT:

{platform_content_text}

OUTPUT RULES:

- Return ONLY problems that require attention.
- Do not list content that is already correct.
- Maximum 8 issues.
- Keep summary to no more than 2 short sentences.
- Keep each issue message concise.
- Use ERROR only when regeneration is necessary.
- Use WARNING for non-blocking improvements.
- Do not repeat large portions of the generated content.
- Do not rewrite the platform content in the review.

Return structured JSON only.
"""

        semantic = self.llm.generate_structured(
            prompt,
            SemanticQualityReview,
            timeout_seconds=(
                settings.quality_timeout_seconds
            ),
            max_output_tokens=(
                settings.quality_max_output_tokens
            ),
        )

        # ---------------------------------------------
        # Merge deterministic + semantic results
        # ---------------------------------------------

        all_issues = deterministic_issues + semantic.issues

        passed = not any(issue.severity == "error" for issue in all_issues)

        return QualityReport(
            passed=passed,
            summary=semantic.summary,
            issues=all_issues,
        )

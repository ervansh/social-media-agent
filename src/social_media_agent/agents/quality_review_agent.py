import json

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

        if (
            youtube is None
            and instagram is None
            and x is None
        ):
            raise ValueError(
                "Quality review requires at least "
                "one generated platform package."
            )

        deterministic_issues = (
            self.validator.validate(
                youtube=youtube,
                instagram=instagram,
                x=x,
            )
        )

        platform_content: list[str] = []

        if youtube is not None:
            platform_content.append(
                "YOUTUBE:\n"
                + youtube.model_dump_json(
                    indent=2
                )
            )

        if instagram is not None:
            platform_content.append(
                "INSTAGRAM:\n"
                + instagram.model_dump_json(
                    indent=2
                )
            )

        if x is not None:
            platform_content.append(
                "X:\n"
                + x.model_dump_json(
                    indent=2
                )
            )

        platform_content_text = (
            "\n\n".join(
                platform_content
            )
        )

        style_guidance = json.dumps(
            {
                "tone": strategy.tone,
                "content_depth":
                    strategy.content_depth,
            },
            ensure_ascii=False,
        )

        master_payload = (
            master_content
            .model_dump_json(
                indent=2,
                exclude={
                    "sources",
                },
            )
        )

        prompt = f"""
You are the quality-control agent for a
social media content generation system.

Review ONLY the generated platform content below.

MASTER CONTENT is the canonical content authority.

STYLE GUIDANCE controls presentation only.
It is NOT factual authority.

STYLE GUIDANCE:

{style_guidance}

MASTER CONTENT:

{master_payload}

GENERATED PLATFORM CONTENT:

{platform_content_text}

==================================================
AUTHORITY RULES
==================================================

- MASTER CONTENT overrides any earlier strategy,
  idea, research synthesis, or discarded wording.

- Do NOT require platform content to preserve a
  strategy core message, must-include point, CTA,
  objective, or factual framing that is absent from
  MASTER CONTENT.

- Do NOT penalize platform content merely because it
  differs from pre-grounding strategy wording.

- Tone and content depth are the only strategy fields
  relevant to this review.

==================================================
QUALITY CHECKS
==================================================

Check for:

- contradiction with MASTER CONTENT,
- factual meaning absent from MASTER CONTENT,
- missing or badly distorted Master message,
- misleading wording,
- poor adaptation to the target platform,
- duplicated or incoherent content,
- excessive generic AI-style language,
- poor fit with requested tone/depth,
- structural/platform-format problems.

Platform Grounding is the primary factual-drift gate,
but factual drift found here is still an ERROR as
defense in depth.

Do not use external knowledge.

Do not introduce new facts.

Use ERROR only when content must be regenerated.
Use WARNING for non-blocking improvements.

OUTPUT RULES:

- Return only problems requiring attention.
- Maximum 8 issues.
- Summary: maximum 2 short sentences.
- Each issue message: concise.
- Do not rewrite platform content in the review.
- Do not demand alignment with factual strategy fields
  that did not survive into MASTER CONTENT.

Return structured JSON only.
"""

        semantic = (
            self.llm.generate_structured(
                prompt,
                SemanticQualityReview,
                timeout_seconds=(
                    settings
                    .quality_timeout_seconds
                ),
                max_output_tokens=(
                    settings
                    .quality_max_output_tokens
                ),
            )
        )

        all_issues = (
            deterministic_issues
            + semantic.issues
        )

        passed = not any(
            issue.severity == "error"
            for issue in all_issues
        )

        return QualityReport(
            passed=passed,
            summary=semantic.summary,
            issues=all_issues,
        )

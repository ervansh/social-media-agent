from social_media_agent.config.settings import settings
from social_media_agent.models.grounding import (
    GroundingReport,
    SemanticGroundingReview,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.research import (
    ResearchBrief,
)
from social_media_agent.services.llm.base import (
    LLMProvider,
)


class GroundingReviewAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    def run(
        self,
        research: ResearchBrief,
        master_content: MasterContent,
    ) -> GroundingReport:

        # ==================================================
        # Compact Source Evidence
        # ==================================================

        selected_sources = research.sources[
            : settings.grounding_max_sources
        ]

        evidence_blocks = []

        for source in selected_sources:

            snippet = source.snippet[
                : settings.grounding_source_max_chars
            ]

            evidence_blocks.append(
                (
                    f"TITLE: {source.title}\n"
                    f"URL: {source.url}\n"
                    f"EVIDENCE: {snippet}"
                )
            )

        source_material = "\n\n".join(
            evidence_blocks
        )

        if not source_material:

            source_material = (
                "No explicit source evidence available."
            )

        # ==================================================
        # Compact Master Content
        # ==================================================

        master_content_for_review = {
            "title": master_content.title,

            "hook": master_content.hook,

            "core_message":
                master_content.core_message,

            "sections": [
                {
                    "heading":
                        section.heading,

                    "key_points":
                        section.key_points,
                }
                for section
                in master_content.sections
            ],

            "key_takeaways":
                master_content.key_takeaways,
        }

        # ==================================================
        # Grounding Prompt
        # ==================================================

        prompt = f"""
You are a strict factual-grounding reviewer.

Review MASTER CONTENT using ONLY SOURCE EVIDENCE.

Do not use external knowledge.

SOURCE EVIDENCE:

{source_material}

MASTER CONTENT:

{master_content_for_review}

Your job is to identify ONLY problematic claims.

IMPORTANT OUTPUT RULE:

Do NOT include claims that are fully supported.

The "issues" list should contain ONLY:

WARNING
The general idea is supported, but the wording is
broader, stronger, more specific, or more certain
than the supplied evidence.

ERROR
The claim is unsupported, contradicted, materially
overstated, based on an invented statistic, or
depends on information missing from the evidence.

If a claim is fully supported:
- do not add it to issues.

If all factual claims are adequately supported:
- return an empty issues list.

GROUNDING RULES:

1. Use only supplied evidence.

2. URLs and titles alone are not evidence.
   Only EVIDENCE text counts.

3. Never infer missing words.

Example:

Evidence:
"GenAI tools will write 70% of..."

Claim:
"70% of test cases are AI-generated."

Verdict:
ERROR

Reason:
The evidence does not identify "test cases" as
the object of the statistic.

4. Statistics require explicit support for BOTH:
   - the number
   - what the number refers to.

5. Recommendations and editorial frameworks are
   not factual claims unless they are presented
   as established research findings.

Example:

"A practical way to assess a tool is to check
coverage, maintainability, and validation."

This is editorial guidance and does not require
proof that one universal framework exists.

6. Do not invent evidence.

7. Be concise.

8. Maximum 8 issues.

9. Summary must be no more than 2 short sentences.

10. Each reason should be no more than 2 short sentences.

11. supporting_source_urls should include only URLs
    that genuinely support or partially support
    the claim.

Return structured JSON only.
"""

        semantic = self.llm.generate_structured(
            prompt,
            SemanticGroundingReview,
            timeout_seconds=(
                settings.grounding_timeout_seconds
            ),
            max_output_tokens=(
                settings.grounding_max_output_tokens
            ),
        )

        # ==================================================
        # Deterministic pass/fail
        # ==================================================
        #
        # WARNING does not block the pipeline.
        # Only ERROR causes grounding failure.
        # ==================================================

        passed = not any(
            issue.severity == "error"
            for issue in semantic.issues
        )

        return GroundingReport(
            passed=passed,
            summary=semantic.summary,
            issues=semantic.issues,
        )
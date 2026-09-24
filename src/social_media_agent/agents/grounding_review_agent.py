from typing import Literal

from pydantic import BaseModel, Field

from social_media_agent.config.settings import settings
from social_media_agent.models.grounding import (
    GroundingIssue,
    GroundingReport,
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


class _GroundingIssueDraft(BaseModel):
    claim_id: int

    severity: Literal[
        "warning",
        "error",
    ]

    reason: str

    supporting_source_urls: list[str] = Field(
        default_factory=list
    )


class _SemanticGroundingReviewDraft(BaseModel):
    summary: str

    issues: list[
        _GroundingIssueDraft
    ] = Field(
        default_factory=list
    )


class GroundingReviewAgent:

    REVIEW_VERSION = 2

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

        source_material = (
            self._build_source_material(
                research
            )
        )

        claims = (
            self._extract_review_claims(
                master_content
            )
        )

        claim_lines = "\n".join(
            (
                f"C{index}: {claim}"
            )
            for index, claim
            in claims.items()
        )

        prompt = f"""
You are a strict factual-grounding reviewer.

Review ONLY the numbered MASTER CLAIMS using
ONLY SOURCE EVIDENCE.

Do not use external knowledge.
Do not create, rewrite, merge, summarize, or infer
claims that are not explicitly listed below.

SOURCE EVIDENCE:

{source_material}

MASTER CLAIMS:

{claim_lines}

Your job is to identify ONLY problematic numbered
claims.

==================================================
OUTPUT CONTRACT
==================================================

For every issue:

- claim_id MUST be the numeric part of one MASTER
  CLAIM identifier.
  Example: for C4 return claim_id=4.

- Do NOT return claim text.
  Python will map claim_id back to the exact original
  Master Content sentence.

- severity must be:
  warning
  or
  error

- Never create an issue for a statement that is not
  present in MASTER CLAIMS.

- Never combine two MASTER CLAIMS into one issue.

WARNING:
The claim's general idea is supported, but its exact
wording is broader, stronger, more specific, or more
certain than the supplied evidence.

ERROR:
The exact claim is unsupported, contradicted,
materially overstated, based on an invented fact, or
depends on information missing from the evidence.

If a claim is fully supported:
- do not add it to issues.

If all factual claims are adequately supported:
- return an empty issues list.

==================================================
GROUNDING RULES
==================================================

1. Use only supplied EVIDENCE text.

2. URLs and source titles alone are not evidence.

3. Never infer missing words.

4. Statistics require explicit support for BOTH:
   - the number
   - what the number refers to.

5. Recommendations, structural labels, review
   instructions, and editorial/meta guidance are not
   factual research claims unless they assert a domain
   fact.

   Examples that should NOT be flagged merely for
   lacking source evidence:

   - "AI Testing Review"
   - "Review the points below."
   - "Use the source-supported points below."
   - "Key Points"
   - "Review the points above."

   These are presentation or evaluation instructions,
   not claims about AI capability, performance,
   adoption, reliability, outcomes, or evidence.

6. Do not invent evidence, consequences, limitations,
   adoption levels, reliability claims, or outcomes.

7. A source demonstrating a capability supports only
   that demonstrated capability and context.

8. A source not stating a limitation does NOT support
   inventing the opposite limitation.

Example:
Evidence says:
"Tool X uses self-healing locators."

Unsupported additions include:
"Self-healing is not widely adopted."
"Self-healing misses defects."
"Self-healing is unreliable in complex systems."

Those statements require their own evidence.

9. Maximum 8 issues.

10. Summary must be no more than 2 short sentences.

11. Each reason should be no more than 2 short
    sentences.

12. supporting_source_urls may contain only URLs from
    SOURCE EVIDENCE that genuinely support or partially
    support the referenced MASTER CLAIM.

Return structured JSON only.
"""

        semantic = (
            self.llm.generate_structured(
                prompt,
                _SemanticGroundingReviewDraft,
                timeout_seconds=(
                    settings
                    .grounding_timeout_seconds
                ),
                max_output_tokens=(
                    settings
                    .grounding_max_output_tokens
                ),
            )
        )

        issues: list[
            GroundingIssue
        ] = []

        seen_claim_ids = set()

        for issue in semantic.issues:

            claim = claims.get(
                issue.claim_id
            )

            if claim is None:
                raise RuntimeError(
                    "Grounding reviewer returned "
                    "an invalid claim_id: "
                    f"{issue.claim_id}"
                )

            if issue.claim_id in seen_claim_ids:
                continue

            seen_claim_ids.add(
                issue.claim_id
            )

            allowed_urls = {
                source.url
                for source
                in research.sources[
                    : settings
                    .grounding_max_sources
                ]
            }

            supporting_urls = [
                url
                for url
                in issue.supporting_source_urls
                if url in allowed_urls
            ]

            issues.append(
                GroundingIssue(
                    severity=(
                        issue.severity
                    ),
                    claim=claim,
                    reason=issue.reason,
                    supporting_source_urls=(
                        supporting_urls
                    ),
                )
            )

        passed = not any(
            issue.severity == "error"
            for issue in issues
        )

        return GroundingReport(
            review_version=self.REVIEW_VERSION,
            passed=passed,
            summary=semantic.summary,
            issues=issues,
        )

    @staticmethod
    def _build_source_material(
        research: ResearchBrief,
    ) -> str:

        selected_sources = research.sources[
            : settings.grounding_max_sources
        ]

        evidence_blocks = []

        for source in selected_sources:

            snippet = source.snippet[
                : settings
                .grounding_source_max_chars
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
            return (
                "No explicit source evidence "
                "available."
            )

        return source_material

    @staticmethod
    def _extract_review_claims(
        master_content: MasterContent,
    ) -> dict[int, str]:

        ordered_claims = [
            master_content.title,
            master_content.hook,
            master_content.core_message,
        ]

        for section in master_content.sections:

            ordered_claims.append(
                section.heading
            )

            ordered_claims.append(
                section.purpose
            )

            ordered_claims.extend(
                section.key_points
            )

        ordered_claims.extend(
            master_content.key_takeaways
        )

        ordered_claims.append(
            master_content.call_to_action
        )

        claims: dict[int, str] = {}
        seen = set()

        for raw_claim in ordered_claims:

            claim = (
                " ".join(
                    raw_claim.split()
                )
                .strip()
            )

            if not claim:
                continue

            normalized = claim.casefold()

            if normalized in seen:
                continue

            seen.add(
                normalized
            )

            claims[
                len(claims) + 1
            ] = claim

        if not claims:
            raise ValueError(
                "Master content contains no "
                "reviewable claims."
            )

        return claims

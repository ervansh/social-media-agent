from typing import Literal

from pydantic import BaseModel, Field

from social_media_agent.config.settings import settings
from social_media_agent.models.grounding import (
    GroundingIssue,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_grounding import (
    PlatformGroundingReport,
)
from social_media_agent.services.grounding.claim_extractor import (
    extract_master_claims,
    extract_platform_claims,
)


class _PlatformClaimDisposition(BaseModel):
    claim_id: int

    verdict: Literal[
        "supported",
        "editorial",
        "warning",
        "error",
    ]

    master_claim_ids: list[int] = Field(
        default_factory=list
    )


class _PlatformClaimDispositionBatch(BaseModel):
    reviews: list[
        _PlatformClaimDisposition
    ] = Field(
        min_length=1
    )


class PlatformGroundingAgent:

    REVIEW_VERSION = 2

    def __init__(
        self,
        llm,
    ):
        self.llm = llm

    def run(
        self,
        *,
        master_content: MasterContent,
        platform: str,
        platform_content: BaseModel,
    ) -> PlatformGroundingReport:

        master_claims = (
            extract_master_claims(
                master_content
            )
        )

        platform_claims = (
            extract_platform_claims(
                platform_content
            )
        )

        master_lines = "\n".join(
            f"M{claim_id}: {claim}"
            for claim_id, claim
            in master_claims.items()
        )

        platform_lines = "\n".join(
            f"P{claim_id}: {claim}"
            for claim_id, claim
            in platform_claims.items()
        )

        prompt = f"""
You are a strict platform-content factual drift
reviewer.

MASTER CONTENT has already passed research grounding.

Your ONLY task is to compare every numbered PLATFORM
STATEMENT against the numbered MASTER CLAIMS.

Do not use external knowledge.
Do not use research evidence.
Do not re-ground MASTER CONTENT.

PLATFORM:
{platform}

MASTER CLAIMS:

{master_lines}

PLATFORM STATEMENTS:

{platform_lines}

==================================================
MANDATORY COVERAGE CONTRACT
==================================================

Return exactly ONE review for EVERY P# statement.

- Do not skip any P#.
- Do not return any P# twice.
- claim_id is the numeric part of P#.
- master_claim_ids may contain only numeric M# IDs.

Python will reject the response if any P# is missing,
duplicated, or invalid.

==================================================
VERDICTS
==================================================

supported:
The entire factual meaning of the P# statement is
already present in one or more mapped M# claims.

For supported:
- master_claim_ids MUST contain at least one M#.

editorial:
The statement is purely presentation, a question,
CTA, label, formatting, or non-factual guidance.

For editorial:
- master_claim_ids may be empty.

warning:
The statement is mostly supported but weakens an
important qualification or becomes slightly broader.

For warning:
- map the relevant M# claims.

error:
The statement introduces any factual meaning absent
from MASTER CONTENT, materially broadens scope,
strengthens certainty, changes attribution, combines
a supported fact with an unsupported consequence, or
adds a new benefit/limitation/capability/outcome.

A statement containing multiple factual clauses is
ERROR if even one factual clause is unsupported.

==================================================
STRICT EXAMPLES
==================================================

MASTER:
M1: Some tools demonstrate self-healing capability.

PLATFORM:
P1: AI tools provide self-healing capability.

=> ERROR. "Some tools" became "AI tools".

MASTER:
M2: Human oversight remains essential.

PLATFORM:
P2: AI may miss subtle defects or UI changes.

=> ERROR. "May miss subtle defects or UI changes" is
a new factual consequence. Human oversight does not
support that consequence.

MASTER:
M3: Some workflows generate tests faster.

PLATFORM:
P3: Some workflows generate tests faster and improve
release speed.

=> ERROR. Release speed is a new benefit.

MASTER:
M4: Review documented capability before relying on it.

PLATFORM:
P4: Review the evidence before adopting the tool.

=> editorial or supported depending on wording.

Do not assume a new statement is supported merely
because it sounds plausible or aligns with the theme.

Return structured JSON only.
"""

        semantic = (
            self.llm.generate_structured(
                prompt,
                _PlatformClaimDispositionBatch,
                timeout_seconds=(
                    settings
                    .platform_grounding_timeout_seconds
                ),
                max_output_tokens=(
                    settings
                    .platform_grounding_max_output_tokens
                ),
            )
        )

        reviews_by_id = {}

        for review in semantic.reviews:

            if (
                review.claim_id
                in reviews_by_id
            ):
                raise RuntimeError(
                    "Platform grounding reviewer "
                    "returned duplicate claim_id: "
                    f"{review.claim_id}"
                )

            reviews_by_id[
                review.claim_id
            ] = review

        expected_ids = set(
            platform_claims
        )

        actual_ids = set(
            reviews_by_id
        )

        if actual_ids != expected_ids:

            missing = sorted(
                expected_ids
                - actual_ids
            )

            unexpected = sorted(
                actual_ids
                - expected_ids
            )

            raise RuntimeError(
                "Platform grounding reviewer "
                "coverage mismatch. "
                f"Missing={missing}, "
                f"Unexpected={unexpected}"
            )

        valid_master_ids = set(
            master_claims
        )

        issues: list[
            GroundingIssue
        ] = []

        for claim_id in sorted(
            reviews_by_id
        ):

            review = reviews_by_id[
                claim_id
            ]

            invalid_master_ids = [
                master_id
                for master_id
                in review.master_claim_ids
                if master_id
                not in valid_master_ids
            ]

            if invalid_master_ids:
                raise RuntimeError(
                    "Platform grounding reviewer "
                    "returned invalid master claim "
                    "IDs: "
                    f"{invalid_master_ids}"
                )

            if (
                review.verdict
                in {
                    "supported",
                    "warning",
                }
                and not review.master_claim_ids
            ):
                raise RuntimeError(
                    "Platform grounding reviewer "
                    f"returned {review.verdict} "
                    "without a mapped Master claim "
                    f"for P{claim_id}."
                )

            if review.verdict not in {
                "warning",
                "error",
            }:
                continue

            if review.verdict == "warning":
                reason = (
                    "Platform wording weakens or "
                    "broadens qualification relative "
                    "to mapped Master Content."
                )
            else:
                reason = (
                    "Platform statement introduces "
                    "or materially changes factual "
                    "meaning beyond Master Content."
                )

            issues.append(
                GroundingIssue(
                    severity=review.verdict,
                    claim=platform_claims[
                        claim_id
                    ],
                    reason=reason,
                    supporting_source_urls=[],
                )
            )

        error_count = sum(
            issue.severity == "error"
            for issue in issues
        )

        warning_count = sum(
            issue.severity == "warning"
            for issue in issues
        )

        passed = (
            error_count == 0
        )

        summary = (
            f"Reviewed {len(platform_claims)} "
            "platform statement(s) against "
            f"{len(master_claims)} Master claim(s): "
            f"{error_count} error(s), "
            f"{warning_count} warning(s)."
        )

        return PlatformGroundingReport(
            platform=platform,
            passed=passed,
            summary=summary,
            issues=issues,
        )

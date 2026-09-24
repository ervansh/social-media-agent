import json

from pydantic import BaseModel

from social_media_agent.config.settings import settings
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_grounding import (
    PlatformGroundingReport,
    SemanticPlatformGroundingReview,
)


class PlatformGroundingAgent:

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

        master_payload = (
            master_content.model_dump(
                mode="json",
                exclude={
                    "sources",
                },
            )
        )

        platform_payload = (
            platform_content.model_dump(
                mode="json"
            )
        )

        master_json = json.dumps(
            master_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        platform_json = json.dumps(
            platform_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        prompt = f"""
You are a platform-content drift reviewer.

MASTER CONTENT has already passed the primary
research-grounding gate.

Do NOT re-review the factual correctness of
MASTER CONTENT.

Your ONLY task is to determine whether PLATFORM
CONTENT changes factual meaning beyond MASTER
CONTENT.

PLATFORM:

{platform}

MASTER CONTENT:

{master_json}

PLATFORM CONTENT:

{platform_json}

==================================================
CORE PRINCIPLE
==================================================

MASTER CONTENT is authoritative.

If PLATFORM CONTENT contains a statement that is
semantically equivalent to MASTER CONTENT, it is
allowed.

Do NOT flag that statement because you personally
believe it needs stronger research evidence.

That question belongs to the previous grounding
stage.

==================================================
ERROR
==================================================

Return ERROR when PLATFORM CONTENT:

- introduces a factual assertion absent from MASTER,
- introduces a new population,
- introduces a new benefit,
- introduces a new capability,
- introduces a new statistic,
- introduces a new named tool or company,
- introduces a new study or source,
- materially broadens a claim,
- converts a limited claim into a general claim,
- converts uncertainty into certainty,
- invents attribution,
- changes attribution,
- connects a person/session/source to a capability
  not connected to it in MASTER CONTENT.

Examples:

MASTER:
"Certain tools demonstrate capability X."

PLATFORM:
"AI tools provide capability X."

=> factual broadening.

MASTER:
"Session A demonstrated test generation."

PLATFORM:
"Session A demonstrated self-healing."

=> attribution error.

==================================================
WARNING
==================================================

Return WARNING when meaning remains substantially
the same but:

- wording becomes slightly broader,
- qualification becomes weaker,
- an important caveat is omitted,
- truncation removes important conditional wording.

Warnings alone do NOT fail the gate.

==================================================
DO NOT FLAG
==================================================

Do not flag:

- style changes,
- sentence restructuring,
- shorter wording,
- formatting,
- hooks,
- editorial questions,
- calls to action,
- semantically equivalent paraphrases,
- claims copied faithfully from MASTER CONTENT.

==================================================
STRICT REVIEW RULES
==================================================

Do not use external knowledge.

Do not use research evidence.

Do not re-ground MASTER CONTENT.

Do not claim MASTER CONTENT contains something
unless that meaning actually appears in the
supplied MASTER CONTENT.

Do not infer missing facts.

Compare only:

MASTER CONTENT
versus
PLATFORM CONTENT.

==================================================
OUTPUT
==================================================

Return only actionable WARNING or ERROR issues.

Do not emit supported findings.

Maximum 6 issues.

Summary maximum 2 short sentences.

Reasons must be concise.

No explanation outside structured JSON.

Return structured JSON only.
"""

        semantic = (
            self.llm.generate_structured(
                prompt,
                SemanticPlatformGroundingReview,
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

        passed = not any(
            issue.severity == "error"
            for issue
            in semantic.issues
        )

        return PlatformGroundingReport(
            platform=platform,
            passed=passed,
            summary=semantic.summary,
            issues=semantic.issues,
        )
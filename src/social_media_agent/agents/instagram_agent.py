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
)


class InstagramAgent:

    def __init__(
        self,
        llm,
    ):
        self.llm = llm

    @staticmethod
    def _build_style_context(
        strategy: ContentStrategy,
    ) -> str:

        style_context = {
            "tone": strategy.tone,
            "content_depth": strategy.content_depth,
        }

        return json.dumps(
            style_context,
            ensure_ascii=False,
        )

    @staticmethod
    def _build_master_context(
        master_content: MasterContent,
    ) -> str:

        payload = master_content.model_dump(
            mode="json",
            exclude={
                "sources",
            },
        )

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def run(
        self,
        strategy: ContentStrategy,
        master_content: MasterContent,
        feedback: str | None = None,
    ) -> InstagramPackage:

        style_context = (
            self._build_style_context(
                strategy
            )
        )

        master_context = (
            self._build_master_context(
                master_content
            )
        )

        revision_feedback = (
            feedback.strip()
            if feedback
            else "None"
        )

        prompt = f"""
You are an Instagram content adaptation agent.

Adapt the already grounded MASTER CONTENT into
Instagram content.

STYLE GUIDANCE:

{style_context}

MASTER CONTENT — FACTUAL SOURCE OF TRUTH:

{master_context}

REVISION FEEDBACK:

{revision_feedback}

==================================================
FACTUAL AUTHORITY
==================================================

MASTER CONTENT is the complete factual ceiling.

STYLE GUIDANCE controls presentation only.

Do not use factual statements from an earlier
strategy, idea, research brief or previous draft
unless they explicitly exist in MASTER CONTENT.

==================================================
GROUNDING RULES
==================================================

Do not introduce a new:

- factual assertion,
- statistic,
- user population,
- capability,
- benefit,
- product,
- tool,
- company,
- study,
- performance improvement,
- adoption statement,
- efficiency statement.

Do not broaden:

"certain tools"
into
"AI tools".

Do not broaden:

"some workflows"
into
"AI testing".

Do not change uncertainty into certainty.

Preserve attribution exactly.

Do not associate a named person, source, study,
session or example with a capability unless
MASTER CONTENT explicitly makes that association.

Do not infer that:

- non-technical people can participate,
- skill barriers are reduced,
- efficiency improves,
- productivity improves,
- cost decreases,
- reliability increases

unless that meaning explicitly exists in
MASTER CONTENT.

REVISION FEEDBACK overrides previous wording.

If feedback identifies an unsupported claim:

remove it or narrow it.

Do NOT surround it with disclaimers.

==================================================
INSTAGRAM REQUIREMENTS
==================================================

Create the required InstagramPackage schema.

Reel hook:

- concise,
- engaging,
- faithful to MASTER CONTENT.

Reel script:

- concise,
- natural,
- no timestamp markers unless explicitly required
  by the schema.

Do NOT produce:

[0-1s]
[1-2s]

or similar timing annotations.

Caption:

- readable,
- useful,
- grounded only in MASTER CONTENT.

Carousel:

Create exactly
{settings.instagram_carousel_slide_count}
slides when the schema requires carousel slides.

Each slide should:

- communicate one clear idea,
- stay concise,
- contain no new factual material.

Call to action:

Editorial CTA language is allowed.

==================================================
FINAL CHECK
==================================================

For every factual sentence ask:

"Is this factual meaning explicitly present in
MASTER CONTENT?"

If no, remove it.

Return structured JSON only.
"""

        return self.llm.generate_structured(
            prompt,
            InstagramPackage,
            timeout_seconds=(
                settings
                .long_generation_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .long_generation_max_output_tokens
            ),
        )
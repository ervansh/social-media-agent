import json

from social_media_agent.config.settings import settings
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    YouTubePackage,
)


class YouTubeAgent:

    def __init__(
        self,
        llm,
    ):
        self.llm = llm

    @staticmethod
    def _build_style_context(
        strategy: ContentStrategy,
    ) -> str:

        # IMPORTANT:
        # Strategy is pre-grounding.
        #
        # Only presentation-oriented fields are allowed
        # to reach platform generation.
        #
        # Do NOT pass:
        # - must_include_points
        # - story_structure
        # - core_message
        # - objective
        # - avoid_claims
        #
        # Those fields may contain factual assumptions
        # that did not survive Master Grounding.

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
    ) -> YouTubePackage:

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
You are a YouTube content adaptation agent.

Your job is to adapt an already grounded MASTER CONTENT
artifact into YouTube content.

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

STYLE GUIDANCE is NOT factual evidence.

Do not use facts merely because they appeared in:

- an earlier strategy,
- an idea,
- research,
- an earlier platform draft,
- revision history.

Only facts explicitly present in MASTER CONTENT may
appear in the YouTube output.

==================================================
GROUNDING RULES
==================================================

1. Preserve factual scope exactly.

2. Never generalize wording.

Examples:

"certain tools"
must not become
"AI tools generally".

"may"
must not become
"will".

"a demonstrated workflow"
must not become
"a standard capability".

3. Do not introduce a new:

- user population,
- audience,
- benefit,
- capability,
- statistic,
- tool,
- company,
- study,
- source,
- adoption claim,
- efficiency claim,
- productivity claim,
- accuracy claim,
- cost claim.

4. Preserve attribution exactly.

If MASTER CONTENT associates a named person,
session, example or source with one capability,
do not use that attribution to support another
capability.

For example:

If a session demonstrates test generation,
do NOT say that same session demonstrates
self-healing unless MASTER CONTENT explicitly says so.

5. Do not infer:

- non-technical-user participation,
- reduced skill barriers,
- improved efficiency,
- faster releases,
- higher accuracy,
- lower cost,
- broader adoption

unless that exact factual meaning exists in
MASTER CONTENT.

6. A caveat in MASTER CONTENT must remain a caveat.

Do not weaken words such as:

- may
- certain
- some
- specific
- can require
- not universal

7. REVISION FEEDBACK overrides previous wording.

If feedback says a claim is too broad:

- remove it, or
- narrow it to the exact MASTER CONTENT wording.

Do not defend the old sentence.

8. Do not solve grounding failures by adding
meta-disclaimers such as:

"This content does not claim..."

"This video only reflects..."

Instead, correct or remove the problematic claim.

==================================================
YOUTUBE REQUIREMENTS
==================================================

Create a YouTubePackage using the required schema.

Title:

- maximum {settings.youtube_title_max_chars} characters,
- clear,
- accurate,
- grounded in MASTER CONTENT.

Description:

- maximum {settings.youtube_description_max_chars} characters,
- summarize MASTER CONTENT,
- do not introduce new factual claims.

Script:

- approximately
  {settings.youtube_script_target_words} words,
- natural spoken language,
- practical and engaging,
- faithful to MASTER CONTENT.

Thumbnail concept:

- visually compelling,
- based only on MASTER CONTENT,
- no new factual assertions.

Short-form hooks:

- concise,
- engaging,
- factually bounded by MASTER CONTENT.

Call to action:

- editorial language is allowed,
- do not introduce factual claims.

==================================================
FINAL CHECK
==================================================

Before returning:

Verify every factual sentence against MASTER CONTENT.

Ask:

"Could this exact factual meaning be found in
MASTER CONTENT?"

If no, remove or rewrite it.

Return structured JSON only.
"""

        return self.llm.generate_structured(
            prompt,
            YouTubePackage,
            timeout_seconds=(
                settings
                .long_generation_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .long_generation_max_output_tokens
            ),
        )
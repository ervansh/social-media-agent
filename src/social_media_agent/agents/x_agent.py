import json

from social_media_agent.config.settings import settings
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    XPackage,
)


class XAgent:

    def __init__(
        self,
        llm,
    ):
        self.llm = llm

    @staticmethod
    def _fit_to_limit(
        text: str,
        limit: int,
    ) -> str:

        text = " ".join(
            text.split()
        )

        if len(text) <= limit:
            return text

        shortened = text[
            : limit - 1
        ].rstrip()

        last_space = shortened.rfind(
            " "
        )

        if last_space > 0:
            shortened = shortened[
                :last_space
            ]

        return (
            shortened.rstrip(
                " ,.;:-"
            )
            + "…"
        )

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
    ) -> XPackage:

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
You are an X content adaptation agent.

Adapt an already grounded MASTER CONTENT artifact
for X.

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

Do not import facts from:

- strategy,
- research,
- selected idea,
- previous drafts,
- earlier platform content.

==================================================
GROUNDING RULES
==================================================

Every factual statement must preserve the meaning
and scope of MASTER CONTENT.

Do not generalize.

For example:

"certain tools"
must remain limited.

Do not change it into:

"AI tools".

Do not convert:

"may"
into
"will".

Do not introduce a new:

- user population,
- benefit,
- capability,
- tool,
- statistic,
- study,
- source,
- efficiency claim,
- performance claim,
- cost claim,
- adoption claim.

Preserve attribution exactly.

IMPORTANT:

Never associate a named source, session, person or
example with a capability that MASTER CONTENT does
not explicitly associate with it.

For example:

If MASTER CONTENT mentions a named session in
connection with test generation, do NOT say that
session demonstrated:

- self-healing,
- script maintenance,
- codeless automation,
- any other capability

unless MASTER CONTENT explicitly says so.

Do not infer:

- non-technical-user participation,
- reduced skill barriers,
- faster work,
- increased efficiency,
- improved accuracy,
- lower cost.

REVISION FEEDBACK overrides all previous wording.

If feedback identifies a claim:

remove it or narrow it.

Do not add disclaimers around unsupported wording.

==================================================
X REQUIREMENTS
==================================================

Main post:

- maximum {settings.x_post_max_chars} characters,
- communicate ONE main idea,
- do not summarize every point from MASTER CONTENT.

Thread:

- exactly {settings.x_thread_post_count} posts
  when required by the schema,
- each post maximum
  {settings.x_post_max_chars} characters,
- preserve qualification and attribution.

Call to action:

Editorial CTA language is allowed.

==================================================
FINAL CHECK
==================================================

For every factual sentence ask:

"Is this exact factual meaning present in
MASTER CONTENT?"

If no, remove it.

Before returning, verify the main post and every
thread post fit within the X character limit.

Return structured JSON only.
"""

        package = self.llm.generate_structured(
            prompt,
            XPackage,
            timeout_seconds=(
                settings
                .long_generation_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .long_generation_max_output_tokens
            ),
        )

        single_post = self._fit_to_limit(
            package.single_post,
            settings.x_post_max_chars,
        )

        thread = [
            self._fit_to_limit(
                post,
                settings.x_post_max_chars,
            )
            for post in package.thread
        ]

        return package.model_copy(
            update={
                "single_post":
                    single_post,
                "thread":
                    thread,
            }
        )
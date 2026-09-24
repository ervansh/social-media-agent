from social_media_agent.config.settings import settings
from social_media_agent.models.content_idea import IdeaBatch
from social_media_agent.models.research import ResearchBrief
from social_media_agent.services.llm.base import LLMProvider


class IdeaAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    def run(
        self,
        research: ResearchBrief,
    ) -> IdeaBatch:

        # --------------------------------------------------
        # Build compact research context
        #
        # We intentionally do NOT send all source snippets
        # again. ResearchAgent has already synthesized them.
        # --------------------------------------------------

        findings = "\n".join(
            f"- {finding}"
            for finding in research.key_findings
        )

        prompt = f"""
You are a social media content strategist.

Create exactly {settings.idea_count} distinct
content ideas based ONLY on the supplied research.

TOPIC:
{research.topic}

TARGET AUDIENCE:
{research.audience}

RESEARCH SUMMARY:
{research.summary}

KEY FINDINGS:
{findings}

Requirements:

- Generate exactly {settings.idea_count} ideas.
- Each idea must be clearly different.
- Keep every idea grounded in the research.
- Do not invent statistics, studies, examples,
  companies, products, or factual claims.
- Focus on practical value for the target audience.
- Avoid generic AI hype.
- The hook should be concise and compelling.
- The angle should explain the specific perspective.
- Rationale should explain why the idea is relevant.
- recommended_platforms may contain only:
  youtube, instagram, x.
- Select only platforms genuinely suitable
  for that specific idea.

Return structured JSON only.
"""

        return self.llm.generate_structured(
            prompt,
            IdeaBatch,
            timeout_seconds=(
                settings.idea_timeout_seconds
            ),
            max_output_tokens=(
                settings.idea_max_output_tokens
            ),
        )
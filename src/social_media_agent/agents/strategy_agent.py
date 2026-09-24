from social_media_agent.config.settings import settings
from social_media_agent.models.content_idea import ContentIdea
from social_media_agent.models.content_strategy import ContentStrategy
from social_media_agent.models.research import ResearchBrief
from social_media_agent.services.llm.base import LLMProvider


class StrategyAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    def run(
        self,
        research: ResearchBrief,
        selected_idea: ContentIdea,
    ) -> ContentStrategy:

        findings = "\n".join(
            f"- {finding}"
            for finding in research.key_findings
        )

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

        source_evidence = "\n\n".join(
            evidence_blocks
        )

        prompt = f"""
You are a senior social media content strategist.

Create a PLATFORM-NEUTRAL content strategy.

TOPIC:
{research.topic}

TARGET AUDIENCE:
{research.audience}

APPROVED IDEA:

{selected_idea.model_dump_json(indent=2)}

RESEARCH SUMMARY:

{research.summary}

KEY FINDINGS:

{findings}

SOURCE EVIDENCE:

{source_evidence}

FACTUAL RULES:

- Use only information supported by SOURCE EVIDENCE.
- Do not turn one example or demonstration into a
  universal product capability.
- If evidence demonstrates that SOME workflows or tools
  can do something, use wording such as:
  "some tools", "some workflows", or
  "AI-assisted approaches can..."

- Do not claim universal capabilities unless the
  evidence explicitly supports them.

- Do not invent statistics.

- Do not infer missing words from incomplete evidence.

- Claims about:
  skill barriers,
  non-technical users,
  productivity,
  speed,
  reliability,
  adoption,
  cost savings,
  accuracy,
  or industry trends
  require explicit evidence.

- Editorial recommendations are allowed.
  Present them as recommendations rather than facts.

- The selected idea is creative direction.
  It is NOT factual evidence.

STRATEGY REQUIREMENTS:

- Define a clear objective.
- Define one core message.
- Choose an appropriate tone.
- Choose content depth:
  short, medium, or deep.
- Define a logical story structure.
- Define must-include points.
- Define claims that should be avoided.
- Define one call to action.
- Keep everything platform-neutral.
- Do not generate platform content.
- Do not include source URLs.

Return structured JSON only.
"""

        return self.llm.generate_structured(
            prompt,
            ContentStrategy,
        )
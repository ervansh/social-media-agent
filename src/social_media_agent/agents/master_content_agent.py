from social_media_agent.config.settings import settings
from social_media_agent.models.content_idea import ContentIdea
from social_media_agent.models.content_strategy import ContentStrategy
from social_media_agent.models.master_content import (
    MasterContent,
    MasterContentDraft,
)
from social_media_agent.models.research import ResearchBrief
from social_media_agent.services.llm.base import LLMProvider


class MasterContentAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    def run(
        self,
        research: ResearchBrief,
        selected_idea: ContentIdea,
        strategy: ContentStrategy,
    ) -> MasterContent:

        findings = "\n".join(
            f"- {finding}"
            for finding
            in research.key_findings
        )

        source_evidence = (
            self._build_source_evidence(
                research
            )
        )

        must_include = "\n".join(
            f"- {point}"
            for point
            in strategy.must_include_points
        )

        avoid_claims = "\n".join(
            f"- {claim}"
            for claim
            in strategy.avoid_claims
        )

        prompt = f"""
You are the master-content creator for a
multi-platform social media content system.

Create canonical platform-neutral content.

The content will later be adapted into
YouTube, Instagram, and X formats.

TOPIC:

{research.topic}

TARGET AUDIENCE:

{research.audience}

APPROVED IDEA:

Title:
{selected_idea.title}

Hook:
{selected_idea.hook}

Angle:
{selected_idea.angle}

IMPORTANT:
The approved idea is creative direction.
It is NOT factual evidence.

RESEARCH SUMMARY:

{research.summary}

KEY FINDINGS:

{findings}

SOURCE EVIDENCE:

{source_evidence}

CONTENT STRATEGY:

Objective:
{strategy.objective}

Core message:
{strategy.core_message}

Tone:
{strategy.tone}

Content depth:
{strategy.content_depth}

Story structure:
{strategy.story_structure}

MUST INCLUDE:

{must_include}

CLAIMS TO AVOID:

{avoid_claims}

CALL TO ACTION:

{strategy.call_to_action}

FACTUAL GROUNDING RULES:

1. SOURCE EVIDENCE is the factual ceiling.

2. Strategy, approved idea, hook, angle, research
   summary, and key findings are NOT evidence.

3. Every factual assertion must be directly supported
   by SOURCE EVIDENCE.

4. Do not convert vague evidence into a specific claim.

5. Never use a statistic unless the evidence explicitly
   states BOTH the number and what it refers to.

6. Do not infer missing words from incomplete evidence.

7. Do not invent:
   - statistics
   - studies
   - companies
   - surveys
   - examples
   - product capabilities
   - limitations
   - adoption levels
   - reliability claims
   - performance outcomes
   - consequences.

8. A demonstrated capability proves only that capability
   in the demonstrated context.

9. Do not invent the opposite of a source claim.

Example:
Evidence:
"Tool X has self-healing locators."

Unsupported:
"Self-healing is not widely adopted."
"Self-healing is unreliable."
"Self-healing may miss defects."

10. Editorial recommendations are allowed, but phrase
    them as recommendations rather than established facts.

11. Avoid universal wording unless SOURCE EVIDENCE
    explicitly supports that scope.

12. If Strategy and SOURCE EVIDENCE conflict,
    SOURCE EVIDENCE always wins.

CONTENT REQUIREMENTS:

- Preserve the useful intent of the approved idea.
- Follow strategy only where it does not exceed evidence.
- Keep the narrative practical and concise.
- Include actionable takeaways.
- Do not include citations or URLs.
- Do not create platform-specific content.
- Do not generate hashtags or timestamps.

Return structured JSON only.
"""

        draft = self.llm.generate_structured(
            prompt,
            MasterContentDraft,
            timeout_seconds=(
                settings
                .master_content_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .master_content_max_output_tokens
            ),
        )

        return MasterContent(
            **draft.model_dump(),
            sources=research.sources,
        )

    @staticmethod
    def _build_source_evidence(
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

        source_evidence = "\n\n".join(
            evidence_blocks
        )

        if not source_evidence:
            return (
                "No explicit source evidence "
                "available."
            )

        return source_evidence

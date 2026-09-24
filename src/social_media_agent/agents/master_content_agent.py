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
        feedback: str | None = None,
        previous_master_content: (
            MasterContent | None
        ) = None,
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

        if feedback is not None:

            if previous_master_content is None:
                raise ValueError(
                    "previous_master_content is "
                    "required for grounding revision."
                )

            prompt = (
                self._build_revision_prompt(
                    research=research,
                    selected_idea=selected_idea,
                    strategy=strategy,
                    findings=findings,
                    source_evidence=(
                        source_evidence
                    ),
                    feedback=feedback,
                    previous_master_content=(
                        previous_master_content
                    ),
                )
            )

        else:

            prompt = (
                self._build_initial_prompt(
                    research=research,
                    selected_idea=selected_idea,
                    strategy=strategy,
                    findings=findings,
                    source_evidence=(
                        source_evidence
                    ),
                )
            )

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

    @staticmethod
    def _build_initial_prompt(
        *,
        research: ResearchBrief,
        selected_idea: ContentIdea,
        strategy: ContentStrategy,
        findings: str,
        source_evidence: str,
    ) -> str:

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

        return f"""
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

    @staticmethod
    def _build_revision_prompt(
        *,
        research: ResearchBrief,
        selected_idea: ContentIdea,
        strategy: ContentStrategy,
        findings: str,
        source_evidence: str,
        feedback: str,
        previous_master_content: MasterContent,
    ) -> str:

        previous_payload = (
            previous_master_content
            .model_dump_json(
                indent=2,
                exclude={
                    "sources",
                },
            )
        )

        return f"""
You are revising previously generated Master Content
after a strict factual-grounding review.

This is an EDIT operation, not a fresh regeneration.

TOPIC:
{research.topic}

TARGET AUDIENCE:
{research.audience}

APPROVED IDEA TITLE:
{selected_idea.title}

STYLE ONLY:
Tone: {strategy.tone}
Content depth: {strategy.content_depth}

IMPORTANT:
Do NOT use the approved idea, original strategy,
research summary, or key findings as factual evidence.

KEY FINDINGS FOR CONTEXT ONLY:
{findings}

SOURCE EVIDENCE — THE ONLY FACTUAL CEILING:

{source_evidence}

PREVIOUS MASTER CONTENT:

{previous_payload}

GROUNDING REVISION FEEDBACK:

{feedback}

REVISION CONTRACT:

1. Revise the PREVIOUS MASTER CONTENT rather than
   regenerating from the original strategy.

2. Every factual assertion in the revised content must
   be directly supported by SOURCE EVIDENCE.

3. For every ERROR:
   - remove the exact claim, OR
   - replace it with a narrower claim directly supported
     by SOURCE EVIDENCE.

4. For every WARNING:
   - narrow, qualify, or remove the exact claim.

5. Do not reintroduce a removed claim under different
   wording elsewhere.

6. Do not add new factual claims during revision.

7. Do not invent limitations, consequences, adoption
   levels, reliability claims, performance outcomes,
   missed defects, false confidence, or human-review
   requirements unless SOURCE EVIDENCE states them.

8. If the original strategy or approved idea conflicts
   with SOURCE EVIDENCE, ignore the conflicting factual
   framing.

9. Preserve the topic, useful editorial structure,
   tone, and platform-neutral nature where possible.

10. Editorial recommendations are allowed only when
    clearly framed as recommendations, not facts.

11. Do not include citations or URLs.

Return the complete revised MasterContentDraft as
structured JSON only.
"""



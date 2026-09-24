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
    ) -> MasterContent:

        # ==================================================
        # Research summary
        # ==================================================

        findings = "\n".join(f"- {finding}" for finding in research.key_findings)

        # ==================================================
        # Compact source evidence
        #
        # IMPORTANT:
        # Use the SAME evidence limits used by the
        # grounding reviewer.
        # ==================================================

        selected_sources = research.sources[: settings.grounding_max_sources]

        evidence_blocks = []

        for source in selected_sources:

            snippet = source.snippet[: settings.grounding_source_max_chars]

            evidence_blocks.append(
                (
                    f"TITLE: {source.title}\n"
                    f"URL: {source.url}\n"
                    f"EVIDENCE: {snippet}"
                )
            )

        source_evidence = "\n\n".join(evidence_blocks)

        if not source_evidence:
            source_evidence = "No explicit source evidence available."

        # ==================================================
        # Strategy data
        # ==================================================

        must_include = "\n".join(f"- {point}" for point in strategy.must_include_points)

        avoid_claims = "\n".join(f"- {claim}" for claim in strategy.avoid_claims)

        # ==================================================
        # Revision feedback
        # ==================================================

        feedback_section = ""

        if feedback:

            feedback_section = f"""
        GROUNDING REVISION FEEDBACK:

        {feedback}

        GROUNDING OVERRIDES THE ORIGINAL STRATEGY.

        If the strategy, approved idea, hook, core message,
        or previous content contains a claim that conflicts
        with this grounding feedback, DO NOT preserve that
        claim merely because it appeared upstream.

        For each ERROR:

        - Remove the claim completely, OR
        - rewrite it into a narrower statement that is
        directly supported by SOURCE EVIDENCE.

        For each WARNING:

        - soften the wording,
        - narrow the scope,
        - qualify the statement,
        - or remove it if the evidence remains too weak.

        Examples:

        ERROR:
        "AI tools eliminate manual scripting."

        Possible revision:
        "Some AI-assisted workflows can generate test cases
        from high-level documentation."

        ERROR:
        "Non-technical users can automate tests."

        If the evidence only says "wider participation",
        do not infer "non-technical users".

        WARNING:
        "AI tools generate tests from user stories."

        Possible revision:
        "Some AI-assisted workflows demonstrate test-case
        generation from high-level documentation."

        Do not reintroduce a removed unsupported claim
        elsewhere in the content.

        Do not introduce new factual claims during revision.
        """

        # ==================================================
        # Prompt
        # ==================================================

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

{feedback_section}

FACTUAL GROUNDING RULES:

1. Every factual assertion must be directly supported
   by SOURCE EVIDENCE.

2. Do not convert vague evidence into a specific claim.

3. Never use a statistic unless the evidence explicitly
   states BOTH:
   - the number
   - exactly what the number refers to.

4. Do not infer missing words from incomplete source text.

Example:

Evidence:
"GenAI tools will write 70% of..."

INVALID:
"70% of test cases will be AI-generated."

The evidence does not explicitly say "test cases".

5. Do not invent:
   - statistics
   - studies
   - companies
   - surveys
   - examples
   - product capabilities
   - industry adoption claims.

6. Editorial frameworks and recommendations are allowed,
   but present them as recommendations rather than
   established facts.

Prefer:
"A practical way to evaluate a tool is..."

Instead of:
"Research proves this is the best framework."

7. If evidence is weak, use cautious wording or omit
   the statement.

8. Human guidance, recommendations, structure, and
   educational framing do not need to be presented
   as scientific facts.

9. A demonstration or example proves only that the
   demonstrated capability exists in that context.
   It does not prove that all AI tools have that
   capability.

10. Avoid universal wording such as:
    - "AI tools can..."
    - "AI tools do..."
    - "AI eliminates..."
    - "AI enables..."
   unless the evidence supports that scope.

Prefer:
    - "Some AI-assisted workflows can..."
    - "Certain tools demonstrate..."
    - "One practical use demonstrated in the
       evidence is..."

11. If Strategy and SOURCE EVIDENCE conflict,
    SOURCE EVIDENCE always wins.

CONTENT REQUIREMENTS:

- Follow the approved idea.
- Follow the content strategy.
- Keep the narrative practical.
- Keep sections concise.
- Preserve the core message.
- Include actionable takeaways.
- Do not include citations.
- Do not output URLs.
- Do not create platform-specific content.
- Do not generate hashtags.
- Do not generate timestamps.

Return structured JSON only.
"""

        # ==================================================
        # Generate
        # ==================================================

        draft = self.llm.generate_structured(
            prompt,
            MasterContentDraft,
            timeout_seconds=(settings.master_content_timeout_seconds),
            max_output_tokens=(settings.master_content_max_output_tokens),
        )

        # ==================================================
        # Attach sources programmatically
        # ==================================================

        return MasterContent(
            **draft.model_dump(),
            sources=research.sources,
        )

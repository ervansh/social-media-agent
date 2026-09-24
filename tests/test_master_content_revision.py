from social_media_agent.agents.master_content_agent import (
    MasterContentAgent,
)
from social_media_agent.models.content_idea import (
    ContentIdea,
)
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContentDraft,
    MasterSection,
)
from social_media_agent.models.research import (
    ResearchBrief,
    SearchResult,
)


class CapturingLLM:

    def __init__(self):
        self.prompt = None

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        self.prompt = prompt

        assert (
            schema
            is MasterContentDraft
        )

        return MasterContentDraft(
            title="Grounded content",
            hook="Review documented capability.",
            core_message=(
                "Some tools demonstrate "
                "self-healing locators."
            ),
            sections=[
                MasterSection(
                    heading="Evidence",
                    purpose=(
                        "Review documented behavior."
                    ),
                    key_points=[
                        (
                            "Some tools demonstrate "
                            "self-healing locators."
                        )
                    ],
                )
            ],
            key_takeaways=[
                (
                    "Verify tool behavior in "
                    "your own workflow."
                )
            ],
            call_to_action=(
                "Review the documentation."
            ),
        )


def build_inputs():

    research = ResearchBrief(
        topic="AI testing",
        audience="QA engineers",
        summary=(
            "Some tools demonstrate "
            "self-healing locators."
        ),
        key_findings=[
            (
                "Some tools demonstrate "
                "self-healing locators."
            )
        ],
        sources=[
            SearchResult(
                title="Source",
                url=(
                    "https://example.com/"
                    "source"
                ),
                snippet=(
                    "Tool X demonstrates "
                    "self-healing locators."
                ),
            )
        ],
    )

    idea = ContentIdea(
        title="Self-healing mistakes",
        hook=(
            "Self-healing tests may "
            "miss defects."
        ),
        angle=(
            "Explore practical limits."
        ),
        target_audience="QA engineers",
        recommended_platforms=[
            "instagram"
        ],
        rationale="Relevant to QA.",
    )

    strategy = ContentStrategy(
        objective="Educate QA engineers.",
        core_message=(
            "Self-healing tests may miss "
            "defects and create false confidence."
        ),
        tone="practical",
        content_depth="medium",
        story_structure=[
            "Capability",
            "Evaluation",
        ],
        must_include_points=[
            (
                "Self-healing tests may "
                "miss defects."
            )
        ],
        avoid_claims=[],
        call_to_action=(
            "Review your workflow."
        ),
    )

    return (
        research,
        idea,
        strategy,
    )


def test_master_prompt_marks_upstream_content_as_non_evidence():

    (
        research,
        idea,
        strategy,
    ) = build_inputs()

    llm = CapturingLLM()

    agent = MasterContentAgent(
        llm=llm
    )

    agent.run(
        research=research,
        selected_idea=idea,
        strategy=strategy,
    )

    assert (
        "SOURCE EVIDENCE is the factual ceiling."
        in llm.prompt
    )

    assert (
        "approved idea is creative direction"
        in llm.prompt
    )

    assert (
        "Strategy, approved idea, hook, angle"
        in llm.prompt
    )


def test_master_prompt_forbids_invented_limitations():

    (
        research,
        idea,
        strategy,
    ) = build_inputs()

    llm = CapturingLLM()

    agent = MasterContentAgent(
        llm=llm
    )

    agent.run(
        research=research,
        selected_idea=idea,
        strategy=strategy,
    )

    assert (
        "Do not invent:"
        in llm.prompt
    )

    assert (
        "- limitations"
        in llm.prompt
    )

    assert (
        "Self-healing may miss defects."
        in llm.prompt
    )

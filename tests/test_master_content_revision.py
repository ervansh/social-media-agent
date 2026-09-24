import pytest

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
    MasterContent,
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
            title="Revised",
            hook=(
                "Some tools demonstrate "
                "self-healing locators."
            ),
            core_message=(
                "Some tools demonstrate "
                "self-healing locators."
            ),
            sections=[
                MasterSection(
                    heading="Evidence",
                    purpose=(
                        "Stay within evidence."
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
                    "Evaluate demonstrated "
                    "capabilities carefully."
                )
            ],
            call_to_action=(
                "Review the evidence."
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
        title="Self-healing tests",
        hook=(
            "Do self-healing tests "
            "miss defects?"
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
            "Limits",
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

    previous = MasterContent(
        title="Self-healing tests",
        hook=(
            "AI cannot fix everything."
        ),
        core_message=(
            "Self-healing tests may "
            "miss defects."
        ),
        sections=[
            MasterSection(
                heading="Limits",
                purpose="Discuss limits",
                key_points=[
                    (
                        "Self-healing is not "
                        "widely adopted."
                    )
                ],
            )
        ],
        key_takeaways=[
            (
                "Human review is always "
                "required."
            )
        ],
        call_to_action=(
            "Review your workflow."
        ),
        sources=[],
    )

    return (
        research,
        idea,
        strategy,
        previous,
    )


def test_revision_uses_previous_master_and_not_strategy_facts():

    (
        research,
        idea,
        strategy,
        previous,
    ) = build_inputs()

    llm = CapturingLLM()

    agent = MasterContentAgent(
        llm=llm
    )

    result = agent.run(
        research=research,
        selected_idea=idea,
        strategy=strategy,
        feedback=(
            "[ERROR]\n"
            "Claim: Self-healing tests "
            "may miss defects.\n"
            "Reason: Unsupported."
        ),
        previous_master_content=(
            previous
        ),
    )

    assert result.title == "Revised"

    assert (
        "PREVIOUS MASTER CONTENT"
        in llm.prompt
    )

    assert (
        "Self-healing is not widely "
        "adopted."
        in llm.prompt
    )

    assert (
        "Self-healing tests may miss "
        "defects and create false confidence."
        not in llm.prompt
    )

    assert (
        "STYLE ONLY:"
        in llm.prompt
    )


def test_revision_requires_previous_master():

    (
        research,
        idea,
        strategy,
        _,
    ) = build_inputs()

    agent = MasterContentAgent(
        llm=CapturingLLM()
    )

    with pytest.raises(
        ValueError,
        match="previous_master_content",
    ):
        agent.run(
            research=research,
            selected_idea=idea,
            strategy=strategy,
            feedback=(
                "[ERROR] Unsupported claim."
            ),
        )

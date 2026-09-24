from social_media_agent.agents.quality_review_agent import (
    QualityReviewAgent,
)
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.models.platform_content import (
    XPackage,
)
from social_media_agent.models.quality import (
    SemanticQualityReview,
)


class FakeValidator:

    def validate(
        self,
        *,
        youtube=None,
        instagram=None,
        x=None,
    ):
        return []


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
            is SemanticQualityReview
        )

        return schema(
            summary="Quality is acceptable.",
            issues=[],
        )


def test_quality_uses_strategy_for_style_only():

    strategy = ContentStrategy(
        objective=(
            "UNSUPPORTED_OBJECTIVE_MARKER"
        ),
        core_message=(
            "UNSUPPORTED_STRATEGY_FACT_MARKER"
        ),
        tone="grounded",
        content_depth="medium",
        story_structure=[
            "Unsupported",
            "Structure",
        ],
        must_include_points=[
            (
                "UNSUPPORTED_MUST_INCLUDE_MARKER"
            )
        ],
        avoid_claims=[],
        call_to_action=(
            "UNSUPPORTED_STRATEGY_CTA_MARKER"
        ),
    )

    master = MasterContent(
        title="Grounded",
        hook="Review documented capability.",
        core_message=(
            "MASTER_FACT_MARKER"
        ),
        sections=[
            MasterSection(
                heading="Evidence",
                purpose="Stay grounded.",
                key_points=[
                    "MASTER_FACT_MARKER"
                ],
            )
        ],
        key_takeaways=[
            "Verify documented behavior."
        ],
        call_to_action=(
            "Review documented capability."
        ),
        sources=[],
    )

    x_content = XPackage(
        single_post=(
            "MASTER_FACT_MARKER"
        ),
        thread=[
            "MASTER_FACT_MARKER",
            "Review documented capability.",
        ],
        call_to_action=(
            "Review documented capability."
        ),
    )

    llm = CapturingLLM()

    agent = QualityReviewAgent(
        llm=llm,
        validator=FakeValidator(),
    )

    result = agent.run(
        strategy=strategy,
        master_content=master,
        x=x_content,
    )

    assert result.passed is True

    assert (
        "MASTER_FACT_MARKER"
        in llm.prompt
    )

    assert (
        '"tone": "grounded"'
        in llm.prompt
    )

    assert (
        '"content_depth": "medium"'
        in llm.prompt
    )

    assert (
        "UNSUPPORTED_STRATEGY_FACT_MARKER"
        not in llm.prompt
    )

    assert (
        "UNSUPPORTED_MUST_INCLUDE_MARKER"
        not in llm.prompt
    )

    assert (
        "UNSUPPORTED_STRATEGY_CTA_MARKER"
        not in llm.prompt
    )

    assert (
        "UNSUPPORTED_OBJECTIVE_MARKER"
        not in llm.prompt
    )

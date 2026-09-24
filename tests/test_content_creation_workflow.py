from social_media_agent.models.content_idea import ContentIdea
from social_media_agent.models.content_strategy import ContentStrategy
from social_media_agent.models.grounding import GroundingReport
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.models.research import (
    ResearchBrief,
    SearchResult,
)
from social_media_agent.workflows.content_creation_workflow import (
    build_content_creation_workflow,
)


class FakeStrategyAgent:

    def run(
        self,
        research,
        selected_idea,
    ):
        return ContentStrategy(
            objective="Educate QA engineers",
            core_message=(
                "AI can assist automation testing "
                "while human validation remains important."
            ),
            tone="Practical",
            content_depth="medium",
            story_structure=[
                "Problem",
                "Approach",
                "Takeaways",
            ],
            must_include_points=[
                "Human validation remains important"
            ],
            avoid_claims=[
                "AI completely replaces testers"
            ],
            call_to_action=(
                "Evaluate one practical AI use case."
            ),
        )


class FakeMasterContentAgent:

    def run(
        self,
        research,
        selected_idea,
        strategy,
        feedback=None,
    ):
        return MasterContent(
            title="AI Automation Testing",
            hook=(
                "AI can assist QA teams "
                "with practical testing workflows."
            ),
            core_message=(
                "AI supports automation testing, "
                "but human validation remains essential."
            ),
            sections=[
                MasterSection(
                    heading="Introduction",
                    purpose=(
                        "Explain how AI supports testing"
                    ),
                    key_points=[
                        (
                            "AI can assist with "
                            "automation activities"
                        ),
                        (
                            "Human validation remains "
                            "important"
                        ),
                    ],
                )
            ],
            key_takeaways=[
                (
                    "Use AI as an assistant rather "
                    "than an unquestioned authority"
                )
            ],
            call_to_action=(
                "Evaluate one practical AI use case."
            ),
            sources=research.sources,
        )


class FakeGroundingAgent:

    def run(
        self,
        research,
        master_content,
    ):
        return GroundingReport(
            passed=True,
            summary=(
                "Master content is adequately "
                "grounded in the supplied research."
            ),
            issues=[],
        )


def create_test_research():
    return ResearchBrief(
        topic="AI automation testing",
        audience="Software testers and QA engineers",
        summary=(
            "AI can assist software testing "
            "and automation workflows."
        ),
        key_findings=[
            (
                "AI-assisted techniques can support "
                "software testing workflows."
            ),
            (
                "Human oversight remains important."
            ),
        ],
        sources=[
            SearchResult(
                title="AI Testing Source",
                url="https://example.com/ai-testing",
                snippet=(
                    "AI can assist selected testing "
                    "activities while human validation "
                    "remains important."
                ),
            )
        ],
    )


def create_test_idea():
    return ContentIdea(
        title="AI Automation Testing",
        hook=(
            "How can AI assist software testers "
            "without replacing human judgment?"
        ),
        angle=(
            "A practical introduction to "
            "AI-assisted testing."
        ),
        target_audience=(
            "Software testers and QA engineers"
        ),
        recommended_platforms=[
            "youtube",
            "instagram",
        ],
        rationale=(
            "The topic provides practical value "
            "for QA professionals."
        ),
    )


def test_content_creation_workflow():
    research = create_test_research()
    idea = create_test_idea()

    workflow = build_content_creation_workflow(
        strategy_agent=FakeStrategyAgent(),
        master_content_agent=FakeMasterContentAgent(),
        grounding_agent=FakeGroundingAgent(),
    )

    result = workflow.invoke(
        {
            "research": research,
            "selected_idea": idea,
        }
    )

    assert result["strategy"] is not None

    assert result["master_content"] is not None

    assert result["grounding_report"] is not None

    assert result["grounding_report"].passed is True

    assert result["grounding_status"] == "passed"

    assert result["review_status"] == "pending"

    assert result["grounding_retry_count"] == 0

    assert (
        result["master_content"].title
        == "AI Automation Testing"
    )
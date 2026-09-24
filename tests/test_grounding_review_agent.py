import pytest

from social_media_agent.agents.grounding_review_agent import (
    GroundingReviewAgent,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.models.research import (
    ResearchBrief,
    SearchResult,
)


def build_research():

    return ResearchBrief(
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


def build_master():

    return MasterContent(
        title="AI Testing",
        hook=(
            "Some tools demonstrate "
            "self-healing locators."
        ),
        core_message=(
            "Self-healing is not widely "
            "adopted."
        ),
        sections=[
            MasterSection(
                heading="Limits",
                purpose="Discuss limits",
                key_points=[
                    (
                        "Self-healing may miss "
                        "unexpected application "
                        "changes."
                    )
                ],
            )
        ],
        key_takeaways=[
            (
                "Evaluate tool behavior "
                "in your own workflow."
            )
        ],
        call_to_action=(
            "Review your test strategy."
        ),
        sources=[],
    )


class ExactClaimLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        assert (
            "C2: Self-healing is not "
            "widely adopted."
            in prompt
        )

        return schema(
            summary=(
                "One claim exceeds "
                "the evidence."
            ),
            issues=[
                {
                    "claim_id": 2,
                    "severity": "error",
                    "reason": (
                        "The evidence does "
                        "not establish adoption."
                    ),
                    "supporting_source_urls": [
                        (
                            "https://example.com/"
                            "source"
                        ),
                        (
                            "https://invalid.example/"
                            "not-source"
                        ),
                    ],
                }
            ],
        )


class InvalidClaimIdLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        return schema(
            summary="Invalid reference.",
            issues=[
                {
                    "claim_id": 999,
                    "severity": "error",
                    "reason":
                        "Invalid reference.",
                    "supporting_source_urls": [],
                }
            ],
        )


class DuplicateClaimLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        return schema(
            summary="Duplicate references.",
            issues=[
                {
                    "claim_id": 2,
                    "severity": "warning",
                    "reason":
                        "First review.",
                    "supporting_source_urls": [],
                },
                {
                    "claim_id": 2,
                    "severity": "error",
                    "reason":
                        "Duplicate review.",
                    "supporting_source_urls": [],
                },
            ],
        )


def test_grounding_report_uses_exact_master_claim():

    agent = GroundingReviewAgent(
        llm=ExactClaimLLM()
    )

    result = agent.run(
        research=build_research(),
        master_content=build_master(),
    )

    assert result.passed is False
    assert len(result.issues) == 1

    issue = result.issues[0]

    assert issue.claim == (
        "Self-healing is not "
        "widely adopted."
    )

    assert (
        issue.supporting_source_urls
        == [
            (
                "https://example.com/"
                "source"
            )
        ]
    )


def test_grounding_rejects_invalid_claim_reference():

    agent = GroundingReviewAgent(
        llm=InvalidClaimIdLLM()
    )

    with pytest.raises(
        RuntimeError,
        match="invalid claim_id",
    ):
        agent.run(
            research=build_research(),
            master_content=build_master(),
        )


def test_grounding_deduplicates_claim_references():

    agent = GroundingReviewAgent(
        llm=DuplicateClaimLLM()
    )

    result = agent.run(
        research=build_research(),
        master_content=build_master(),
    )

    assert len(result.issues) == 1

    assert result.issues[0].claim == (
        "Self-healing is not "
        "widely adopted."
    )

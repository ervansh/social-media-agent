import re

import pytest
from pydantic import BaseModel

from social_media_agent.agents.platform_grounding_agent import (
    PlatformGroundingAgent,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    CarouselSlide,
    InstagramPackage,
)


class DummyPlatformContent(BaseModel):
    text: str


class AllSupportedLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        platform_ids = [
            int(value)
            for value in re.findall(
                r"^P(\d+):",
                prompt,
                flags=re.MULTILINE,
            )
        ]

        return schema(
            reviews=[
                {
                    "claim_id": claim_id,
                    "verdict": "supported",
                    "master_claim_ids": [1],
                }
                for claim_id
                in platform_ids
            ]
        )


class DriftDetectingLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        reviews = []

        for match in re.finditer(
            r"^P(\d+): (.+)$",
            prompt,
            flags=re.MULTILINE,
        ):

            claim_id = int(
                match.group(1)
            )

            claim = match.group(2)

            if (
                "miss subtle defects"
                in claim
            ):
                verdict = "error"
                master_ids = []
            else:
                verdict = "supported"
                master_ids = [1]

            reviews.append(
                {
                    "claim_id": claim_id,
                    "verdict": verdict,
                    "master_claim_ids":
                        master_ids,
                }
            )

        return schema(
            reviews=reviews
        )


class IncompleteReviewLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        return schema(
            reviews=[
                {
                    "claim_id": 1,
                    "verdict": "supported",
                    "master_claim_ids": [1],
                }
            ]
        )


def build_master():

    return MasterContent.model_construct(
        title="AI Testing",
        hook=(
            "AI-assisted testing."
        ),
        core_message=(
            "Human oversight remains "
            "essential."
        ),
        sections=[],
        key_takeaways=[],
        call_to_action=(
            "Review documented capability."
        ),
        sources=[],
    )


def test_platform_grounding_passes_when_all_statements_supported():

    agent = PlatformGroundingAgent(
        llm=AllSupportedLLM()
    )

    platform_content = (
        DummyPlatformContent(
            text=(
                "AI-assisted testing."
            )
        )
    )

    result = agent.run(
        master_content=build_master(),
        platform="x",
        platform_content=platform_content,
    )

    assert result.passed is True
    assert result.platform == "x"
    assert result.issues == []


def test_platform_grounding_binds_drift_to_exact_platform_statement():

    agent = PlatformGroundingAgent(
        llm=DriftDetectingLLM()
    )

    instagram = InstagramPackage(
        reel_hook=(
            "Review AI testing carefully."
        ),
        reel_script=(
            "Human oversight remains essential. "
            "AI may miss subtle defects or UI changes."
        ),
        caption=(
            "Review documented capability."
        ),
        carousel_slides=[
            CarouselSlide(
                position=1,
                headline=(
                    "Human oversight"
                ),
                body=(
                    "Human oversight remains "
                    "essential."
                ),
            )
        ],
        hashtags=[],
        call_to_action=(
            "Review documented capability."
        ),
    )

    result = agent.run(
        master_content=build_master(),
        platform="instagram",
        platform_content=instagram,
    )

    assert result.passed is False

    assert any(
        issue.severity == "error"
        and issue.claim
        == (
            "AI may miss subtle defects "
            "or UI changes."
        )
        for issue in result.issues
    )


def test_platform_grounding_rejects_incomplete_review_coverage():

    agent = PlatformGroundingAgent(
        llm=IncompleteReviewLLM()
    )

    platform_content = (
        DummyPlatformContent(
            text=(
                "First statement. "
                "Second statement."
            )
        )
    )

    with pytest.raises(
        RuntimeError,
        match="coverage mismatch",
    ):
        agent.run(
            master_content=build_master(),
            platform="x",
            platform_content=platform_content,
        )

from pydantic import BaseModel

from social_media_agent.agents.platform_grounding_agent import (
    PlatformGroundingAgent,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_grounding import (
    SemanticPlatformGroundingReview,
)


class DummyPlatformContent(BaseModel):
    text: str


class FakeLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        assert (
            schema
            is SemanticPlatformGroundingReview
        )

        return schema(
            summary=(
                "No platform factual drift."
            ),
            issues=[],
        )


def test_platform_grounding_passes_without_errors():

    agent = PlatformGroundingAgent(
        llm=FakeLLM()
    )

    master = MasterContent.model_construct(
        title="AI Testing",
        hook="AI-assisted testing.",
        core_message=(
            "AI-assisted approaches can "
            "help generate test cases."
        ),
        sections=[],
        key_takeaways=[],
        sources=[],
    )

    platform_content = (
        DummyPlatformContent(
            text=(
                "AI-assisted approaches can "
                "help generate test cases."
            )
        )
    )

    result = agent.run(
        master_content=master,
        platform="x",
        platform_content=platform_content,
    )

    assert result.passed is True
    assert result.platform == "x"
    assert result.issues == []
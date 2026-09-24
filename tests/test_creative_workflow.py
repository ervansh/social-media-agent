from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    ImageBrief,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.workflows.creative_workflow import (
    build_creative_workflow,
)


class FakeCreativeAgent:

    def run(
        self,
        strategy,
        master_content,
        youtube=None,
        instagram=None,
        x=None,
    ):
        return CreativeAssetBundle(
            images=[
                ImageBrief(
                    platform="youtube",
                    asset_type="thumbnail",
                    width=3840,
                    height=2160,
                    objective="Increase clarity",
                    visual_concept=(
                        "QA engineer reviewing "
                        "AI-generated tests"
                    ),
                    text_overlay="AI TESTING?",
                    image_prompt=(
                        "Professional QA engineer "
                        "reviewing AI-assisted testing "
                        "workflow, clean composition"
                    ),
                    negative_prompt=(
                        "cluttered interface"
                    ),
                )
            ]
        )


def test_creative_workflow():

    strategy = ContentStrategy(
        objective="Educate",
        core_message=(
            "AI assists testing workflows."
        ),
        tone="Practical",
        content_depth="medium",
        story_structure=[
            "Problem",
            "Solution",
        ],
        must_include_points=[
            "Human validation matters"
        ],
        call_to_action="Evaluate one use case.",
    )

    master_content = MasterContent(
        title="AI Testing",
        hook="AI is changing testing.",
        core_message=(
            "AI assists testing workflows."
        ),
        sections=[
            MasterSection(
                heading="Introduction",
                purpose="Explain AI testing",
                key_points=[
                    "Human review remains important"
                ],
            )
        ],
        key_takeaways=[
            "Use AI responsibly"
        ],
        call_to_action="Evaluate one use case.",
        sources=[],
    )

    workflow = build_creative_workflow(
        creative_agent=FakeCreativeAgent()
    )

    result = workflow.invoke(
        {
            "strategy": strategy,
            "master_content": master_content,
        }
    )

    assert result[
        "creative_assets"
    ] is not None

    assert (
        len(
            result[
                "creative_assets"
            ].images
        )
        == 1
    )
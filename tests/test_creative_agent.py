import pytest
from pydantic import ValidationError

from social_media_agent.agents.creative_agent import (
    CreativeAgent,
    _ImageBriefDraft,
)
from social_media_agent.config.settings import settings
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.models.platform_content import (
    XPackage,
    YouTubePackage,
)


class FakeCreativeLLM:

    def __init__(self):
        self.calls = []

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        self.calls.append(
            schema.__name__
        )

        # Image draft
        if "objective" in schema.model_fields:

            return schema(
                objective="Create a clear visual.",
                visual_concept="Simple QA workflow visual.",
                text_overlay="AI-assisted testing",
                image_prompt=(
                    "Modern QA workflow interface "
                    "with user story and test case."
                ),
                negative_prompt=(
                    "clutter, unreadable text"
                ),
            )

        raise AssertionError(
            f"Unexpected schema: {schema}"
        )


def test_creative_agent_separates_youtube_and_x_images():

    llm = FakeCreativeLLM()

    agent = CreativeAgent(
        llm=llm
    )

    strategy = ContentStrategy(
        objective="Explain AI-assisted testing.",
        core_message="AI can assist QA workflows.",
        tone="professional",
        content_depth="medium",
        story_structure=[
            "problem",
            "solution",
        ],
        must_include_points=[
            "user stories",
        ],
        avoid_claims=[],
        call_to_action="Learn more.",
    )

    master_content = MasterContent(
        title="AI Testing",
        hook="Turn stories into tests.",
        core_message=(
            "AI-assisted workflows can help "
            "generate tests from requirements."
        ),
        sections=[
            MasterSection(
                heading="Overview",
                purpose="Explain the workflow.",
                key_points=[
                    "Use requirements as input."
                ],
            )
        ],
        key_takeaways=[
            "Human review remains important."
        ],
        call_to_action="Explore the workflow.",
    )

    youtube = YouTubePackage(
        title="AI Testing",
        description="Description",
        script="Script",
        thumbnail_concept=(
            "User story transforming into test cases."
        ),
        shorts_hooks=[
            "Turn stories into tests."
        ],
        call_to_action="Learn more.",
    )

    x = XPackage(
        single_post=(
            "AI-assisted testing can help "
            "turn requirements into tests."
        ),
        thread=[
            "Post 1",
            "Post 2",
            "Post 3",
            "Post 4",
            "Post 5",
        ],
        call_to_action="Learn more.",
    )

    bundle = agent.run(
        strategy=strategy,
        master_content=master_content,
        youtube=youtube,
        x=x,
    )

    assert len(bundle.images) == 2

    assert len(bundle.storyboards) == 0

    assert (
        bundle.images[0].platform
        == "youtube"
    )

    assert (
        bundle.images[0].asset_type
        == "thumbnail"
    )

    assert (
        bundle.images[1].platform
        == "x"
    )

    assert (
        bundle.images[1].asset_type
        == "supporting_visual"
    )

    # One small LLM call per image.
    assert len(llm.calls) == 2

class CapturingCreativeLLM:

    def __init__(self):
        self.calls = []

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        self.calls.append(
            {
                "prompt": prompt,
                "schema": schema,
                "timeout_seconds":
                    timeout_seconds,
                "max_output_tokens":
                    max_output_tokens,
            }
        )

        if "objective" in schema.model_fields:
            return schema(
                objective="Create a clear visual.",
                visual_concept=(
                    "Minimal QA workflow visual."
                ),
                text_overlay="QA REVIEW",
                image_prompt=(
                    "Minimal QA workspace, one "
                    "laptop, clean visual hierarchy."
                ),
                negative_prompt=(
                    "clutter, unreadable text"
                ),
            )

        scene_count = (
            settings
            .instagram_reel_scene_count
        )

        return schema(
            scenes=[
                {
                    "narration":
                        f"Scene {index} narration.",
                    "visual_direction":
                        f"Scene {index} visual.",
                    "on_screen_text":
                        f"Scene {index}",
                }
                for index in range(
                    1,
                    scene_count + 1,
                )
            ]
        )


def test_image_brief_schema_rejects_runaway_prompt():

    with pytest.raises(
        ValidationError
    ):
        _ImageBriefDraft(
            objective="Objective",
            visual_concept="Concept",
            text_overlay="Overlay",
            image_prompt="x" * 901,
            negative_prompt="none",
        )


def test_image_brief_uses_bounded_context_and_dedicated_budget(
    monkeypatch,
):

    monkeypatch.setattr(
        settings,
        "creative_source_context_max_chars",
        80,
    )

    llm = CapturingCreativeLLM()

    agent = CreativeAgent(
        llm=llm
    )

    agent._generate_image_brief(
        platform="instagram",
        asset_type="carousel_slide_1",
        width=1080,
        height=1350,
        source_context=(
            "Supported source context "
            * 20
            + "TAIL_SHOULD_NOT_APPEAR"
        ),
        tone="practical",
    )

    call = llm.calls[0]

    assert (
        call["max_output_tokens"]
        == settings
        .creative_image_brief_max_output_tokens
    )

    assert (
        "TAIL_SHOULD_NOT_APPEAR"
        not in call["prompt"]
    )

    schema_json = (
        call["schema"]
        .model_json_schema()
    )

    assert (
        schema_json[
            "properties"
        ][
            "image_prompt"
        ][
            "maxLength"
        ]
        == 900
    )


def test_storyboard_uses_bounded_schema_and_python_scene_numbers():

    llm = CapturingCreativeLLM()

    agent = CreativeAgent(
        llm=llm
    )

    storyboard = (
        agent._generate_storyboard(
            platform="instagram",
            asset_type="reel_storyboard",
            source_context=(
                "Short grounded reel content."
            ),
            tone="practical",
        )
    )

    assert [
        scene.scene_number
        for scene
        in storyboard.scenes
    ] == list(
        range(
            1,
            settings
            .instagram_reel_scene_count
            + 1,
        )
    )

    assert (
        llm.calls[0][
            "max_output_tokens"
        ]
        == settings
        .creative_storyboard_max_output_tokens
    )

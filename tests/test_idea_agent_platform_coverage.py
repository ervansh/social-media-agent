from social_media_agent.agents.idea_agent import (
    IdeaAgent,
)
from social_media_agent.models.research import (
    ResearchBrief,
)


class FakeCoverageLLM:

    def generate_structured(
        self,
        prompt,
        schema,
        *,
        timeout_seconds=None,
        max_output_tokens=None,
    ):

        schema_json = (
            schema.model_json_schema()
        )

        flexible_count = (
            schema_json[
                "properties"
            ][
                "flexible_ideas"
            ].get(
                "minItems",
                0,
            )
        )

        flexible_ideas = [
            {
                "title":
                    f"Flexible idea {index}",
                "hook":
                    f"Flexible hook {index}",
                "angle":
                    f"Flexible angle {index}",
                "target_audience":
                    "QA engineers",
                "recommended_platforms":
                    ["youtube", "x"],
                "rationale":
                    "Grounded flexible idea.",
            }
            for index in range(
                flexible_count
            )
        ]

        return schema(
            youtube_idea={
                "title":
                    "Deep-dive QA workflow",
                "hook":
                    "See the workflow end to end.",
                "angle":
                    "Long-form explanation.",
                "target_audience":
                    "QA engineers",
                "additional_platforms":
                    [],
                "rationale":
                    "Suitable for a walkthrough.",
            },
            instagram_idea={
                "title":
                    "5 AI testing checkpoints",
                "hook":
                    "Swipe through the checkpoints.",
                "angle":
                    "Visual carousel checklist.",
                "target_audience":
                    "QA engineers",
                "additional_platforms":
                    ["x"],
                "rationale":
                    "Works as swipeable education.",
            },
            x_idea={
                "title":
                    "AI testing thread",
                "hook":
                    "A concise QA thread.",
                "angle":
                    "Practical discussion thread.",
                "target_audience":
                    "QA engineers",
                "additional_platforms":
                    [],
                "rationale":
                    "Suitable for X discussion.",
            },
            flexible_ideas=flexible_ideas,
        )


def research():

    return ResearchBrief.model_construct(
        topic="AI automation testing",
        audience="QA engineers",
        summary=(
            "AI can assist selected "
            "testing workflows."
        ),
        key_findings=[
            (
                "Human validation remains "
                "important."
            )
        ],
        sources=[],
    )


def test_idea_agent_guarantees_platform_coverage(
    monkeypatch,
):

    monkeypatch.setattr(
        "social_media_agent.agents."
        "idea_agent.settings.idea_count",
        5,
    )

    agent = IdeaAgent(
        llm=FakeCoverageLLM()
    )

    result = agent.run(
        research()
    )

    assert len(result.ideas) == 5

    covered = {
        platform
        for idea in result.ideas
        for platform
        in idea.recommended_platforms
    }

    assert covered == {
        "youtube",
        "instagram",
        "x",
    }

    assert (
        "instagram"
        in result.ideas[1]
        .recommended_platforms
    )


def test_idea_agent_respects_configurable_count(
    monkeypatch,
):

    monkeypatch.setattr(
        "social_media_agent.agents."
        "idea_agent.settings.idea_count",
        4,
    )

    agent = IdeaAgent(
        llm=FakeCoverageLLM()
    )

    result = agent.run(
        research()
    )

    assert len(result.ideas) == 4

    assert any(
        "instagram"
        in idea.recommended_platforms
        for idea in result.ideas
    )

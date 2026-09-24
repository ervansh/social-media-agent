from langgraph.graph import END, START, StateGraph

from social_media_agent.models.platform_content_state import (
    PlatformContentState,
)


def build_platform_content_workflow(
    youtube_agent,
    instagram_agent,
    x_agent,
):

    def generate_platform_content(
        state: PlatformContentState,
    ) -> dict:

        platforms = set(state["platforms"])

        updates = {}

        if "youtube" in platforms:
            updates["youtube"] = youtube_agent.run(
                strategy=state["strategy"],
                master_content=state["master_content"],
            )

        if "instagram" in platforms:
            updates["instagram"] = instagram_agent.run(
                strategy=state["strategy"],
                master_content=state["master_content"],
            )

        if "x" in platforms:
            updates["x"] = x_agent.run(
                strategy=state["strategy"],
                master_content=state["master_content"],
            )

        updates["generation_status"] = "complete"

        return updates

    graph = StateGraph(PlatformContentState)

    graph.add_node(
        "generate_platform_content",
        generate_platform_content,
    )

    graph.add_edge(
        START,
        "generate_platform_content",
    )

    graph.add_edge(
        "generate_platform_content",
        END,
    )

    return graph.compile()
from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from social_media_agent.models.creative_state import (
    CreativeState,
)


def build_creative_workflow(
    creative_agent,
):

    def creative_node(
        state: CreativeState,
    ) -> dict:

        bundle = creative_agent.run(
            strategy=state["strategy"],
            master_content=state[
                "master_content"
            ],
            youtube=state.get(
                "youtube"
            ),
            instagram=state.get(
                "instagram"
            ),
            x=state.get(
                "x"
            ),
        )

        return {
            "creative_assets": bundle
        }

    graph = StateGraph(
        CreativeState
    )

    graph.add_node(
        "creative",
        creative_node,
    )

    graph.add_edge(
        START,
        "creative",
    )

    graph.add_edge(
        "creative",
        END,
    )

    return graph.compile()
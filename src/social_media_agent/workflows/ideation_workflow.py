from langgraph.graph import END, START, StateGraph

from social_media_agent.agents.idea_agent import IdeaAgent
from social_media_agent.agents.research_agent import ResearchAgent
from social_media_agent.models.ideation_state import (
    IdeationState,
)


def build_ideation_workflow(
    research_agent: ResearchAgent,
    idea_agent: IdeaAgent,
):

    def research_node(
        state: IdeationState,
    ) -> dict:

        research = research_agent.run(
            topic=state["topic"],
            audience=state["audience"],
        )

        return {
            "research": research,
        }

    def idea_node(
        state: IdeationState,
    ) -> dict:

        ideas = idea_agent.run(
            state["research"]
        )

        return {
            "ideas": ideas,
            "approval_status": "pending",
        }

    graph = StateGraph(IdeationState)

    graph.add_node(
        "research",
        research_node,
    )

    graph.add_node(
        "generate_ideas",
        idea_node,
    )

    graph.add_edge(
        START,
        "research",
    )

    graph.add_edge(
        "research",
        "generate_ideas",
    )

    graph.add_edge(
        "generate_ideas",
        END,
    )

    return graph.compile()
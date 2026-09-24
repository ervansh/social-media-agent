from langgraph.graph import END, START, StateGraph

from social_media_agent.models.workflow_state import WorkflowState
from social_media_agent.services.llm.base import LLMProvider


def build_bootstrap_workflow(provider: LLMProvider):

    def prepare_prompt(state: WorkflowState) -> dict:
        prompt = (
            "Respond briefly and confirm that the AI workflow is operational.\n"
            f"Input: {state['input_text']}"
        )

        return {
            "prompt": prompt
        }

    def call_llm(state: WorkflowState) -> dict:
        response = provider.generate(state["prompt"])

        return {
            "response": response
        }

    graph = StateGraph(WorkflowState)

    graph.add_node("prepare_prompt", prepare_prompt)
    graph.add_node("call_llm", call_llm)

    graph.add_edge(START, "prepare_prompt")
    graph.add_edge("prepare_prompt", "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile()
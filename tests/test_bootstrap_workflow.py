from social_media_agent.workflows.bootstrap_workflow import (
    build_bootstrap_workflow,
)


class FakeLLMProvider:

    def generate(self, prompt: str) -> str:
        return "SYSTEM_READY"


def test_bootstrap_workflow():

    workflow = build_bootstrap_workflow(
        FakeLLMProvider()
    )

    result = workflow.invoke(
        {
            "input_text": "test"
        }
    )

    assert result["response"] == "SYSTEM_READY"
    assert result["prompt"]
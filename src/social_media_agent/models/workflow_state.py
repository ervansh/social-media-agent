from typing import TypedDict


class WorkflowState(TypedDict, total=False):
    input_text: str
    prompt: str
    response: str
    error: str
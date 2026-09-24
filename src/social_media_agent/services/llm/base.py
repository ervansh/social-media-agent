from typing import Protocol, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):

    def generate(
        self,
        prompt: str,
    ) -> str:
        ...

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        timeout_seconds: int | None = None,
        max_output_tokens: int | None = None,
    ) -> T:
        ...    
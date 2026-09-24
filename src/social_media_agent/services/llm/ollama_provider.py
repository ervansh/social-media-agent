from typing import TypeVar

import requests
from pydantic import BaseModel

from social_media_agent.config.settings import settings
from pydantic import ValidationError

T = TypeVar("T", bound=BaseModel)


class OllamaProvider:

    CHAT_ENDPOINT = "/api/chat"

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.ollama_timeout_seconds
        self.temperature = settings.llm_temperature

    def _chat(
        self,
        prompt: str,
        response_format: dict | None = None,
        timeout_seconds: int | None = None,
        max_output_tokens: int | None = None,
    ) -> str:

        options = {
            "temperature": self.temperature,
        }

        if max_output_tokens is not None:
            options["num_predict"] = max_output_tokens

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "stream": False,
            "think": settings.ollama_think,
            "options": options,
        }

        if response_format:
            payload["format"] = response_format

        response = requests.post(
            f"{self.base_url}{self.CHAT_ENDPOINT}",
            json=payload,
            timeout=(timeout_seconds or self.timeout),
        )

        response.raise_for_status()

        return response.json()["message"]["content"]

    def generate(self, prompt: str) -> str:
        return self._chat(prompt)

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        timeout_seconds: int | None = None,
        max_output_tokens: int | None = None,
    ) -> T:

        content = self._chat(
            prompt,
            response_format=schema.model_json_schema(),
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
        )

        try:

            return schema.model_validate_json(content)

        except ValidationError as exc:

            preview = content[-500:]

            raise RuntimeError(
                "Ollama returned invalid or incomplete "
                "structured JSON. "
                f"Model: {self.model}. "
                f"Response length: {len(content)} characters. "
                f"Response tail: {preview!r}"
            ) from exc

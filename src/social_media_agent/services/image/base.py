from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ImageGenerationResult:
    image_bytes: bytes

    width: int
    height: int

    provider: str
    model: str

    file_extension: str


class ImageProvider(Protocol):

    def generate(
        self,
        prompt: str,
        width: int,
        height: int,
    ) -> ImageGenerationResult:
        ...
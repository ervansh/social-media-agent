from typing import Literal

from pydantic import BaseModel, Field

Platform = Literal[
    "youtube",
    "instagram",
    "x",
]


class ImageBrief(BaseModel):
    platform: Platform
    asset_type: str

    width: int
    height: int

    objective: str
    visual_concept: str

    text_overlay: str | None = None

    image_prompt: str
    negative_prompt: str | None = None


class StoryboardScene(BaseModel):
    scene_number: int

    narration: str
    visual_direction: str
    on_screen_text: str | None = None


class VideoStoryboard(BaseModel):
    platform: Platform
    asset_type: str

    scenes: list[StoryboardScene] = Field(min_length=1)


class CreativeAssetBundle(BaseModel):
    images: list[ImageBrief] = Field(default_factory=list)

    storyboards: list[VideoStoryboard] = Field(default_factory=list)

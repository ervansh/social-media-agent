from pydantic import BaseModel, Field


class CarouselSlide(BaseModel):
    position: int
    headline: str
    body: str


class YouTubePackage(BaseModel):
    title: str
    description: str
    script: str

    chapters: list[str] = Field(default_factory=list)

    thumbnail_concept: str

    shorts_hooks: list[str] = Field(
        min_length=1
    )

    call_to_action: str


class InstagramPackage(BaseModel):
    reel_hook: str
    reel_script: str
    caption: str

    carousel_slides: list[CarouselSlide] = Field(
        min_length=1
    )

    hashtags: list[str] = Field(
        default_factory=list
    )

    call_to_action: str


class XPackage(BaseModel):
    single_post: str

    thread: list[str] = Field(
        min_length=2
    )

    call_to_action: str
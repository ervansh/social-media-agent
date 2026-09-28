from pydantic import BaseModel, Field


class GeneratedImageAsset(BaseModel):
    platform: str
    asset_type: str

    storage_key: str

    provider: str
    model: str

    requested_width: int
    requested_height: int

    generated_width: int
    generated_height: int

    prompt: str


class GeneratedVideoAsset(BaseModel):
    platform: str
    asset_type: str
    storyboard_asset_type: str

    storage_key: str

    provider: str
    model: str

    width: int
    height: int
    fps: int

    duration_seconds: float
    scene_count: int

    source_image_storage_keys: list[str] = Field(
        min_length=1
    )


class GeneratedAssetBundle(BaseModel):
    images: list[GeneratedImageAsset] = Field(
        default_factory=list
    )

    videos: list[GeneratedVideoAsset] = Field(
        default_factory=list
    )

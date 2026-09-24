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


class GeneratedAssetBundle(BaseModel):
    images: list[GeneratedImageAsset] = Field(
        default_factory=list
    )
from pydantic import BaseModel


class StoredMediaAsset(BaseModel):
    source_storage_key: str
    store_provider: str
    object_key: str
    content_type: str
    size_bytes: int
    etag: str | None = None
    version_id: str | None = None

from pydantic import BaseModel, Field

from social_media_agent.models.research import SearchResult


class MasterSection(BaseModel):
    heading: str
    purpose: str
    key_points: list[str] = Field(min_length=1)


class MasterContentDraft(BaseModel):
    title: str
    hook: str
    core_message: str

    sections: list[MasterSection] = Field(min_length=1)

    key_takeaways: list[str] = Field(min_length=1)

    call_to_action: str


class MasterContent(MasterContentDraft):
    sources: list[SearchResult] = Field(default_factory=list)
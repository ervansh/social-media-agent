from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class SearchPlan(BaseModel):
    queries: list[str] = Field(min_length=1)


class ResearchSynthesis(BaseModel):
    summary: str
    key_findings: list[str]


class ResearchBrief(BaseModel):
    topic: str
    audience: str
    summary: str
    key_findings: list[str]
    sources: list[SearchResult]
from typing import Protocol

from social_media_agent.models.research import SearchResult


class SearchProvider(Protocol):

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        ...
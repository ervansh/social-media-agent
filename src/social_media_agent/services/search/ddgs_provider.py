from ddgs import DDGS

from social_media_agent.config.settings import settings
from social_media_agent.models.research import SearchResult


class DDGSSearchProvider:

    def search(
        self,
        query: str,
        limit: int,
    ) -> list[SearchResult]:

        results = DDGS().text(
            query=query,
            region=settings.search_region,
            safesearch="moderate",
            max_results=limit,
        )

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("href", ""),
                snippet=item.get("body", ""),
            )
            for item in results
            if item.get("href")
        ]
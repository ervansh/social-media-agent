from dataclasses import dataclass

import requests

from social_media_agent.services.publishing.instagram_graph_client import (
    InstagramGraphClient,
)
from social_media_agent.services.publishing.media_url_resolver import (
    MediaUrlResolver,
)


@dataclass(frozen=True)
class InstagramPreflightResult:
    account_id: str
    username: str
    media_count: int | None
    media_url: str | None
    media_url_accessible: bool


class InstagramPublishingPreflight:

    def __init__(
        self,
        *,
        client: InstagramGraphClient,
        media_url_resolver: MediaUrlResolver,
        http_session: requests.Session | None = None,
        timeout_seconds: int = 20,
    ):
        self.client = client
        self.media_url_resolver = (
            media_url_resolver
        )
        self.http_session = (
            http_session
            or requests.Session()
        )
        self.timeout_seconds = (
            timeout_seconds
        )

    def verify(
        self,
        *,
        storage_key: str | None = None,
    ) -> InstagramPreflightResult:

        account = (
            self.client.get_account_info()
        )

        media_url = None
        accessible = False

        if storage_key:
            media_url = (
                self.media_url_resolver.resolve(
                    storage_key
                )
            )

            accessible = (
                self._is_publicly_accessible(
                    media_url
                )
            )

            if not accessible:
                raise RuntimeError(
                    "Resolved Instagram media URL "
                    "is not publicly accessible."
                )

        media_count = account.get(
            "media_count"
        )

        return InstagramPreflightResult(
            account_id=str(
                account["id"]
            ),
            username=str(
                account["username"]
            ),
            media_count=(
                int(media_count)
                if media_count is not None
                else None
            ),
            media_url=media_url,
            media_url_accessible=accessible,
        )

    def _is_publicly_accessible(
        self,
        media_url: str,
    ) -> bool:

        response = (
            self.http_session.get(
                media_url,
                stream=True,
                allow_redirects=True,
                timeout=self.timeout_seconds,
            )
        )

        return (
            200
            <= response.status_code
            < 300
        )

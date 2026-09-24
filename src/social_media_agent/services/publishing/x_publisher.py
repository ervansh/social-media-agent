import requests

from social_media_agent.config.settings import settings
from social_media_agent.models.publication import (
    PublicationRequest,
    PublicationResult,
)


class XPublisher:

    CREATE_POST_ENDPOINT = "/tweets"

    def __init__(self):

        if not settings.x_user_access_token:
            raise ValueError(
                "X_USER_ACCESS_TOKEN is required "
                "for live X publishing."
            )

        self.base_url = (
            settings.x_api_base_url.rstrip("/")
        )

        self.access_token = (
            settings.x_user_access_token
        )

        self.timeout = (
            settings.x_request_timeout_seconds
        )

    def publish(
        self,
        request: PublicationRequest,
    ) -> PublicationResult:

        if request.platform != "x":
            raise ValueError(
                "XPublisher only supports X."
            )

        text = request.payload.get(
            "text"
        )

        if not text:
            raise ValueError(
                "X publication payload "
                "does not contain text."
            )

        response = requests.post(
            (
                f"{self.base_url}"
                f"{self.CREATE_POST_ENDPOINT}"
            ),
            headers={
                "Authorization": (
                    f"Bearer {self.access_token}"
                ),
                "Content-Type":
                    "application/json",
            },
            json={
                "text": text,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        data = response.json()

        post_data = data.get(
            "data",
            {}
        )

        post_id = post_data.get(
            "id"
        )

        return PublicationResult(
            platform="x",
            status="published",
            message=(
                "X post published successfully."
            ),
            external_id=post_id,
            response_payload=data,
        )
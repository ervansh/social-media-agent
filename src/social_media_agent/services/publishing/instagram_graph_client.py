from typing import Any

import requests

from social_media_agent.config.settings import (
    settings,
)


class InstagramGraphAPIError(
    RuntimeError
):
    pass


class InstagramGraphClient:

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_version: str | None = None,
        instagram_user_id: str | None = None,
        access_token: str | None = None,
        timeout_seconds: int | None = None,
        session: requests.Session | None = None,
    ):
        self.base_url = (
            base_url
            or settings.instagram_api_base_url
        ).rstrip("/")

        self.api_version = (
            api_version
            or settings.instagram_api_version
        ).strip("/")

        self.instagram_user_id = (
            instagram_user_id
            if instagram_user_id is not None
            else settings.instagram_user_id
        )

        self.access_token = (
            access_token
            if access_token is not None
            else settings.instagram_access_token
        )

        self.timeout_seconds = (
            timeout_seconds
            or settings
            .instagram_request_timeout_seconds
        )

        self.session = (
            session
            or requests.Session()
        )

    def create_image_container(
        self,
        *,
        image_url: str,
        caption: str | None = None,
        is_carousel_item: bool = False,
    ) -> str:

        if not image_url:
            raise ValueError(
                "image_url is required."
            )

        data: dict[str, Any] = {
            "image_url": image_url,
        }

        if caption:
            data["caption"] = caption

        if is_carousel_item:
            data["is_carousel_item"] = "true"

        payload = self._request(
            "POST",
            (
                f"{self.instagram_user_id}"
                "/media"
            ),
            data=data,
        )

        return self._require_id(
            payload,
            context=(
                "Instagram image container"
            ),
        )

    def create_carousel_container(
        self,
        *,
        child_container_ids: list[str],
        caption: str,
    ) -> str:

        max_items = (
            settings
            .instagram_max_carousel_items
        )

        if not (
            2
            <= len(child_container_ids)
            <= max_items
        ):
            raise ValueError(
                "Instagram carousel requires "
                f"between 2 and {max_items} "
                "media items."
            )

        if any(
            not container_id
            for container_id
            in child_container_ids
        ):
            raise ValueError(
                "Instagram carousel contains "
                "an empty child container ID."
            )

        payload = self._request(
            "POST",
            (
                f"{self.instagram_user_id}"
                "/media"
            ),
            data={
                "media_type": "CAROUSEL",
                "children": ",".join(
                    child_container_ids
                ),
                "caption": caption,
            },
        )

        return self._require_id(
            payload,
            context=(
                "Instagram carousel container"
            ),
        )

    def publish_container(
        self,
        container_id: str,
    ) -> str:

        if not container_id:
            raise ValueError(
                "container_id is required."
            )

        payload = self._request(
            "POST",
            (
                f"{self.instagram_user_id}"
                "/media_publish"
            ),
            data={
                "creation_id":
                    container_id,
            },
        )

        return self._require_id(
            payload,
            context=(
                "Instagram published media"
            ),
        )

    def _validate_configuration(
        self,
    ) -> None:

        missing = []

        if not self.instagram_user_id:
            missing.append(
                "INSTAGRAM_USER_ID"
            )

        if not self.access_token:
            missing.append(
                "INSTAGRAM_ACCESS_TOKEN"
            )

        if missing:
            raise InstagramGraphAPIError(
                "Missing Instagram live "
                "publishing configuration: "
                + ", ".join(missing)
            )

    def _url(
        self,
        path: str,
    ) -> str:

        return (
            f"{self.base_url}/"
            f"{self.api_version}/"
            f"{path.lstrip('/')}"
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        self._validate_configuration()

        response = self.session.request(
            method=method,
            url=self._url(path),
            headers={
                "Authorization": (
                    f"Bearer "
                    f"{self.access_token}"
                ),
            },
            data=data,
            params=params,
            timeout=self.timeout_seconds,
        )

        try:
            payload = response.json()

        except ValueError as exc:
            raise InstagramGraphAPIError(
                "Instagram API returned "
                "a non-JSON response."
            ) from exc

        if not response.ok:

            error = payload.get(
                "error",
                {},
            )

            message = error.get(
                "message",
                "Unknown Instagram API error.",
            )

            error_type = error.get(
                "type",
                "unknown",
            )

            error_code = error.get(
                "code",
                "unknown",
            )

            raise InstagramGraphAPIError(
                "Instagram API request failed. "
                f"type={error_type}, "
                f"code={error_code}, "
                f"message={message}"
            )

        if not isinstance(
            payload,
            dict,
        ):
            raise InstagramGraphAPIError(
                "Instagram API returned "
                "an unexpected response shape."
            )

        return payload

    @staticmethod
    def _require_id(
        payload: dict[str, Any],
        *,
        context: str,
    ) -> str:

        object_id = payload.get(
            "id"
        )

        if not object_id:
            raise InstagramGraphAPIError(
                f"{context} response "
                "did not contain an ID."
            )

        return str(
            object_id
        )

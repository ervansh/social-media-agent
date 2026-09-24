from typing import Protocol

from social_media_agent.models.publication import (
    PublicationRequest,
    PublicationResult,
)


class Publisher(Protocol):

    def publish(
        self,
        request: PublicationRequest,
    ) -> PublicationResult:
        ...
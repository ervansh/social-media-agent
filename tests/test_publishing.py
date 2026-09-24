from social_media_agent.models.publication import (
    PublicationRequest,
)
from social_media_agent.services.publishing.dry_run_publisher import (
    DryRunPublisher,
)


def test_dry_run_publisher():

    publisher = DryRunPublisher()

    request = PublicationRequest(
        run_id="test-run",
        platform="x",
        payload={
            "text": "Test post"
        },
    )

    result = publisher.publish(
        request
    )

    assert result.platform == "x"

    assert (
        result.status
        == "dry_run"
    )

    assert (
        result.external_id
        is None
    )
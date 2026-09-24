from unittest.mock import (
    Mock,
    patch,
)

from social_media_agent.models.publication import (
    PublicationRequest,
)
from social_media_agent.services.publishing.x_publisher import (
    XPublisher,
)


@patch(
    "social_media_agent.services.publishing."
    "x_publisher.requests.post"
)
def test_x_publisher(
    mock_post,
    monkeypatch,
):

    monkeypatch.setattr(
        "social_media_agent.services."
        "publishing.x_publisher."
        "settings.x_user_access_token",
        "fake-token",
    )

    response = Mock()

    response.json.return_value = {
        "data": {
            "id": "123456",
            "text": "Test post",
        }
    }

    response.raise_for_status.return_value = (
        None
    )

    mock_post.return_value = response

    publisher = XPublisher()

    request = PublicationRequest(
        run_id="test-run",
        platform="x",
        payload={
            "text": "Test post",
        },
    )

    result = publisher.publish(
        request
    )

    assert result.status == "published"

    assert (
        result.external_id
        == "123456"
    )

    mock_post.assert_called_once()
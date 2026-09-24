from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.publishing.dry_run_publisher import (
    DryRunPublisher,
)
from social_media_agent.services.publishing.instagram_graph_client import (
    InstagramGraphClient,
)
from social_media_agent.services.publishing.instagram_publisher import (
    InstagramPublisher,
)
from social_media_agent.services.publishing.media_url_resolver import (
    PublicBaseUrlMediaUrlResolver,
)
from social_media_agent.services.publishing.x_publisher import (
    XPublisher,
)


def get_publishers():

    mode = settings.publishing_mode.lower()

    if mode == "dry_run":

        dry_run = DryRunPublisher()

        return {
            "youtube": dry_run,
            "instagram": dry_run,
            "x": dry_run,
        }

    if mode == "live":

        return {
            # YouTube intentionally has no live
            # publisher yet. PublishingService will
            # report it as blocked instead of
            # simulating success in live mode.
            "instagram": InstagramPublisher(
                client=InstagramGraphClient(),
                media_url_resolver=(
                    PublicBaseUrlMediaUrlResolver()
                ),
            ),

            "x": XPublisher(),
        }

    raise ValueError(
        "Unsupported PUBLISHING_MODE: "
        f"{settings.publishing_mode}"
    )

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.publishing.dry_run_publisher import (
    DryRunPublisher,
)
from social_media_agent.services.publishing.x_publisher import (
    XPublisher,
)


def get_publishers():

    if settings.publishing_mode == "dry_run":

        dry_run = DryRunPublisher()

        return {
            "youtube": dry_run,
            "instagram": dry_run,
            "x": dry_run,
        }

    if settings.publishing_mode == "live":

        return {
            # These remain simulated until their
            # real integrations are implemented.
            "youtube": DryRunPublisher(),
            "instagram": DryRunPublisher(),

            # X can publish live.
            "x": XPublisher(),
        }

    raise ValueError(
        "Unsupported PUBLISHING_MODE: "
        f"{settings.publishing_mode}"
    )
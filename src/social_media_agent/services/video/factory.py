from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.services.video.ffmpeg_reel_renderer import (
    DeterministicReelRenderer,
)


def get_video_renderer():

    renderer = (
        settings.video_renderer
        .strip()
        .lower()
    )

    if renderer == "ffmpeg":
        return DeterministicReelRenderer()

    raise ValueError(
        "Unsupported VIDEO_RENDERER: "
        f"{settings.video_renderer}"
    )

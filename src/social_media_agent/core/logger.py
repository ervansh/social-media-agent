import sys

from loguru import logger

from social_media_agent.config.settings import settings


def configure_logging():

    logger.remove()

    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )

    logger.add(
        "logs/social_media_agent.log",
        rotation="10 MB",
        retention="30 days",
        level=settings.log_level,
    )

    return logger
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
)

from social_media_agent.config.settings import settings


class Base(DeclarativeBase):
    pass


def _prepare_sqlite_directory() -> None:
    prefix = "sqlite:///"

    if not settings.database_url.startswith(prefix):
        return

    db_path = settings.database_url.removeprefix(prefix)

    if db_path == ":memory:":
        return

    Path(db_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )


_prepare_sqlite_directory()


engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
)


SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def initialize_database() -> None:
    # Import required so SQLAlchemy knows all mappings.
    from social_media_agent.persistence import models  # noqa: F401

    Base.metadata.create_all(
        bind=engine
    )
import re
from pathlib import PurePosixPath


def normalize_storage_key(
    storage_key: str,
) -> str:

    if (
        not storage_key
        or not storage_key.strip()
    ):
        raise ValueError(
            "Media storage key cannot be empty."
        )

    raw_key = storage_key.strip()

    if (
        raw_key.startswith(
            (
                "/",
                "\\",
            )
        )
        or re.match(
            r"^[a-zA-Z]:[\\/]",
            raw_key,
        )
        or "://" in raw_key
    ):
        raise ValueError(
            "Media storage key must be a "
            "relative storage key."
        )

    normalized = raw_key.replace(
        "\\",
        "/",
    )

    parts = PurePosixPath(
        normalized
    ).parts

    if (
        not parts
        or any(
            part
            in {
                "",
                ".",
                "..",
            }
            for part
            in parts
        )
    ):
        raise ValueError(
            "Media storage key contains "
            "an invalid path segment."
        )

    return "/".join(
        parts
    )

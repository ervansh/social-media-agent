import re

from pydantic import BaseModel

from social_media_agent.models.master_content import (
    MasterContent,
)


def normalize_claim(
    value: str,
) -> str:

    return " ".join(
        value.split()
    ).strip()


def extract_master_claims(
    master_content: MasterContent,
) -> dict[int, str]:

    ordered_claims = [
        master_content.title,
        master_content.hook,
        master_content.core_message,
    ]

    for section in master_content.sections:

        ordered_claims.append(
            section.heading
        )

        ordered_claims.append(
            section.purpose
        )

        ordered_claims.extend(
            section.key_points
        )

    ordered_claims.extend(
        master_content.key_takeaways
    )

    ordered_claims.append(
        master_content.call_to_action
    )

    return _deduplicate(
        ordered_claims
    )


def extract_platform_claims(
    platform_content: BaseModel,
) -> dict[int, str]:

    raw_values: list[str] = []

    _collect_strings(
        platform_content.model_dump(
            mode="json"
        ),
        raw_values,
    )

    segments: list[str] = []

    for value in raw_values:

        normalized = normalize_claim(
            value
        )

        if not normalized:
            continue

        parts = re.split(
            r"(?<=[.!?])\s+|\n+",
            normalized,
        )

        for part in parts:

            claim = normalize_claim(
                part
            )

            if claim:
                segments.append(
                    claim
                )

    return _deduplicate(
        segments
    )


def _collect_strings(
    value,
    output: list[str],
) -> None:

    if isinstance(
        value,
        str,
    ):
        output.append(
            value
        )
        return

    if isinstance(
        value,
        dict,
    ):
        for child in value.values():
            _collect_strings(
                child,
                output,
            )
        return

    if isinstance(
        value,
        list,
    ):
        for child in value:
            _collect_strings(
                child,
                output,
            )


def _deduplicate(
    values: list[str],
) -> dict[int, str]:

    claims: dict[int, str] = {}
    seen = set()

    for raw_value in values:

        value = normalize_claim(
            raw_value
        )

        if not value:
            continue

        key = value.casefold()

        if key in seen:
            continue

        seen.add(
            key
        )

        claims[
            len(claims) + 1
        ] = value

    if not claims:
        raise ValueError(
            "No reviewable claims were found."
        )

    return claims

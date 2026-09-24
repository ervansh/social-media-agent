import json
from pathlib import Path

import streamlit as st

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.generated_assets import (
    GeneratedAssetBundle,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.ui.dependencies import (
    get_persistence_service,
)


def _resolve_generated_asset_path(
    storage_key: str,
) -> Path | None:

    root = Path(
        settings.generated_assets_dir
    ).resolve()

    normalized = (
        storage_key
        .replace("\\", "/")
    )

    parts = [
        part
        for part in normalized.split("/")
        if part
    ]

    if (
        not parts
        or any(
            part in {".", ".."}
            for part in parts
        )
    ):
        return None

    candidate = (
        root
        .joinpath(*parts)
        .resolve()
    )

    try:
        candidate.relative_to(
            root
        )

    except ValueError:
        return None

    if not candidate.is_file():
        return None

    return candidate


def _render_generated_media_preview(
    persistence,
    run_id: str,
) -> None:

    payload = (
        persistence.get_latest_payload(
            run_id,
            ArtifactType.GENERATED_ASSETS,
        )
    )

    if payload is None:
        return

    bundle = (
        GeneratedAssetBundle
        .model_validate(
            payload
        )
    )

    instagram_assets = [
        asset
        for asset in bundle.images
        if asset.platform
        == "instagram"
    ]

    if not instagram_assets:
        return

    st.divider()

    st.subheader(
        "Generated Instagram Media"
    )

    st.caption(
        "Preview the actual generated JPEG "
        "assets before approving this run."
    )

    columns = st.columns(3)

    for index, asset in enumerate(
        instagram_assets
    ):

        target = columns[
            index % len(columns)
        ]

        file_path = (
            _resolve_generated_asset_path(
                asset.storage_key
            )
        )

        with target:

            if file_path is None:

                st.warning(
                    "Generated asset file "
                    "is unavailable."
                )

                st.caption(
                    asset.storage_key
                )

                continue

            st.image(
                str(file_path),
                caption=(
                    f"{asset.asset_type} "
                    f"({asset.generated_width}×"
                    f"{asset.generated_height})"
                ),
                use_container_width=True,
            )

            st.caption(
                f"Provider: {asset.provider} "
                f"· Model: {asset.model}"
            )


def render():

    st.title("Content Review")

    persistence = (
        get_persistence_service()
    )

    runs = persistence.list_runs(
        limit=100
    )

    if not runs:
        st.info(
            "No content runs available."
        )
        return

    run_map = {
        run.id: run
        for run in runs
    }

    selected_run_id = st.selectbox(
        "Select content run",
        options=list(
            run_map.keys()
        ),
        format_func=lambda run_id: (
            f"{run_map[run_id].topic} "
            f"— {run_map[run_id].status}"
        ),
    )

    run = run_map[
        selected_run_id
    ]

    st.divider()

    st.subheader(
        run.topic
    )

    col1, col2 = st.columns(2)

    col1.write(
        f"**Audience:** {run.audience}"
    )

    col2.write(
        f"**Status:** `{run.status}`"
    )

    st.caption(
        f"Run ID: {run.id}"
    )

    artifacts = (
        persistence
        .get_latest_artifacts(
            run.id
        )
    )

    if not artifacts:
        st.warning(
            "No artifacts found."
        )
        return

    st.divider()

    st.subheader(
        "Latest Artifacts"
    )

    for artifact in sorted(
        artifacts,
        key=lambda item: (
            item.artifact_type,
            item.platform or "",
        ),
    ):

        platform_label = (
            f" — {artifact.platform}"
            if artifact.platform
            else ""
        )

        title = (
            f"{artifact.artifact_type}"
            f"{platform_label}"
            f" · v{artifact.version}"
        )

        with st.expander(
            title
        ):

            editor_key = (
                f"artifact_"
                f"{artifact.id}"
            )

            payload_text = json.dumps(
                artifact.payload,
                indent=2,
                ensure_ascii=False,
            )

            edited_payload = st.text_area(
                "Artifact JSON",
                value=payload_text,
                height=400,
                key=editor_key,
            )

            if st.button(
                "Save New Version",
                key=(
                    f"save_"
                    f"{artifact.id}"
                ),
            ):

                try:
                    payload = json.loads(
                        edited_payload
                    )

                except json.JSONDecodeError as exc:

                    st.error(
                        f"Invalid JSON: {exc}"
                    )

                else:

                    persistence.save_payload(
                        run_id=run.id,
                        artifact_type=(
                            artifact.artifact_type
                        ),
                        platform=(
                            artifact.platform
                        ),
                        payload=payload,
                    )

                    st.success(
                        "New artifact version saved."
                    )

                    st.rerun()

    _render_generated_media_preview(
        persistence,
        run.id,
    )

    st.divider()

    st.subheader(
        "Human Review"
    )

    review_note = st.text_area(
        "Review note",
        placeholder=(
            "Optional approval or rejection note"
        ),
    )

    approve_col, reject_col = (
        st.columns(2)
    )

    if approve_col.button(
        "Approve for Publishing",
        type="primary",
        use_container_width=True,
    ):

        persistence.save_payload(
            run_id=run.id,
            artifact_type=(
                ArtifactType.REVIEW_DECISION
            ),
            payload={
                "decision": "approved",
                "note": review_note,
            },
        )

        persistence.update_status(
            run.id,
            RunStatus.APPROVED_FOR_PUBLISHING.value,
        )

        st.success(
            "Content approved for publishing."
        )

        st.rerun()

    if reject_col.button(
        "Reject",
        use_container_width=True,
    ):

        persistence.save_payload(
            run_id=run.id,
            artifact_type=(
                ArtifactType.REVIEW_DECISION
            ),
            payload={
                "decision": "rejected",
                "note": review_note,
            },
        )

        persistence.update_status(
            run.id,
            RunStatus.REJECTED.value,
        )

        st.warning(
            "Content rejected."
        )

        st.rerun()
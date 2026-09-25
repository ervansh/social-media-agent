import streamlit as st

from social_media_agent.config.settings import settings
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import RunStatus
from social_media_agent.ui.dependencies import (
    get_instagram_run_preflight_service,
    get_persistence_service,
    get_publishing_service,
)


def render():

    st.title("Publishing")

    persistence = get_persistence_service()
    publishing = get_publishing_service()

    # ==================================================
    # Load only approved content runs
    # ==================================================

    runs = [
        run
        for run in persistence.list_runs(limit=100)
        if run.status
        == RunStatus.APPROVED_FOR_PUBLISHING.value
    ]

    if not runs:
        st.info(
            "No approved content is ready "
            "for publishing."
        )
        return

    # ==================================================
    # Select content run
    # ==================================================

    run_map = {
        run.id: run
        for run in runs
    }

    selected_run_id = st.selectbox(
        "Approved content run",
        options=list(run_map.keys()),
        format_func=lambda run_id: (
            f"{run_map[run_id].topic}"
            f" — "
            f"{run_map[run_id].audience}"
        ),
    )

    selected_run = run_map[
        selected_run_id
    ]

    st.divider()

    st.subheader(
        selected_run.topic
    )

    col1, col2 = st.columns(2)

    col1.write(
        f"**Audience:** "
        f"{selected_run.audience}"
    )

    col2.write(
        f"**Status:** "
        f"`{selected_run.status}`"
    )

    st.caption(
        f"Run ID: {selected_run.id}"
    )

    # ==================================================
    # Publishing Mode
    # ==================================================

    st.divider()

    st.subheader(
        "Publishing Mode"
    )

    publishing_mode = (
        settings.publishing_mode.lower()
    )

    if publishing_mode == "dry_run":

        st.warning(
            "DRY-RUN mode is enabled. "
            "Nothing will be published "
            "to any social media platform."
        )

        button_text = (
            "Run Publishing Dry Run"
        )

    elif publishing_mode == "live":

        st.error(
            "LIVE publishing mode is enabled. "
            "Supported platforms may publish "
            "content to real social accounts."
        )

        button_text = (
            "Publish Approved Content"
        )

    else:

        st.error(
            "Invalid PUBLISHING_MODE configured: "
            f"{settings.publishing_mode}"
        )

        return

    # ==================================================
    # Platform readiness information
    # ==================================================

    st.subheader(
        "Platform Publishing"
    )

    st.write(
        """
Current publishing support:

- **X** — live text publishing available
- **Instagram** — live image/carousel publishing available; requires public generated JPEG media
- **YouTube** — live publishing not implemented yet; requires a final video file
"""
    )

    # ==================================================
    # Instagram Preflight
    # ==================================================

    instagram_payload = (
        persistence.get_latest_payload(
            selected_run_id,
            ArtifactType.PLATFORM_CONTENT,
            platform="instagram",
        )
    )

    if instagram_payload is not None:

        st.divider()

        st.subheader(
            "Instagram Preflight"
        )

        st.caption(
            "Non-destructive readiness check. "
            "No Instagram content is published."
        )

        st.write(
            f"**Media resolver:** "
            f"`{settings.media_url_provider}`"
        )

        if st.button(
            "Run Instagram Preflight",
            use_container_width=True,
            key=(
                "instagram_preflight_"
                f"{selected_run_id}"
            ),
        ):

            try:

                with st.spinner(
                    "Verifying Instagram account "
                    "and generated media..."
                ):

                    preflight = (
                        get_instagram_run_preflight_service()
                    )

                    result = preflight.verify(
                        selected_run_id
                    )

            except Exception as exc:

                st.error(
                    "Instagram preflight failed: "
                    f"{exc}"
                )

            else:

                if result.ready:

                    st.success(
                        "Instagram is READY "
                        "for controlled publishing."
                    )

                else:

                    st.warning(
                        "Instagram preflight "
                        "completed but is not ready."
                    )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                col1.metric(
                    "Instagram User",
                    result.username,
                )

                col2.metric(
                    "Generated Media",
                    len(
                        result.media_storage_keys
                    ),
                )

                col3.metric(
                    "Verified URLs",
                    len(
                        result.media_urls
                    ),
                )

                col4.metric(
                    "Storage",
                    (
                        "READY"
                        if result.storage_verified
                        else "NOT READY"
                    ),
                )

                st.caption(
                    "Instagram User ID: "
                    f"{result.account_id}"
                )

                st.caption(
                    "Image provider: "
                    + ", ".join(
                        result.image_providers
                    )
                )

                st.caption(
                    "Media delivery provider: "
                    f"{result.media_provider}"
                )

                if (
                    result.media_count
                    is not None
                ):
                    st.caption(
                        "Existing Instagram media: "
                        f"{result.media_count}"
                    )

                with st.expander(
                    "Verified Instagram media"
                ):

                    for index, (
                        storage_key,
                        media_url,
                    ) in enumerate(
                        zip(
                            result.media_storage_keys,
                            result.media_urls,
                            strict=True,
                        ),
                        start=1,
                    ):

                        st.write(
                            f"**{index}.** "
                            f"`{storage_key}`"
                        )

                        st.code(
                            media_url,
                            language=None,
                        )

    # ==================================================
    # Execute publishing
    # ==================================================

    if st.button(
        button_text,
        type="primary",
        use_container_width=True,
    ):

        try:

            with st.spinner(
                "Checking publishing readiness "
                "and processing platforms..."
            ):

                batch = publishing.publish(
                    selected_run_id
                )

        except Exception as exc:

            st.error(
                "Publishing operation failed: "
                f"{exc}"
            )

            return

        # ==============================================
        # Display result
        # ==============================================

        st.divider()

        st.subheader(
            "Publishing Result"
        )

        if not batch.results:

            st.warning(
                "No platform content was found "
                "for this run."
            )

            return

        for result in batch.results:

            platform_name = (
                result.platform.upper()
            )

            # ------------------------------------------
            # Dry Run
            # ------------------------------------------

            if result.status == "dry_run":

                st.success(
                    f"{platform_name}: "
                    f"{result.message}"
                )

            # ------------------------------------------
            # Successfully Published
            # ------------------------------------------

            elif result.status == "published":

                st.success(
                    f"{platform_name}: "
                    f"{result.message}"
                )

                if result.external_id:

                    st.caption(
                        "Published content ID: "
                        f"{result.external_id}"
                    )

            # ------------------------------------------
            # Blocked
            # ------------------------------------------

            elif result.status == "blocked":

                st.warning(
                    f"{platform_name}: "
                    f"{result.message}"
                )

            # ------------------------------------------
            # Failed
            # ------------------------------------------

            elif result.status == "failed":

                st.error(
                    f"{platform_name}: "
                    f"{result.message}"
                )

            # ------------------------------------------
            # Unknown status
            # ------------------------------------------

            else:

                st.info(
                    f"{platform_name}: "
                    f"{result.status} — "
                    f"{result.message}"
                )

            # ------------------------------------------
            # Optional provider response
            # ------------------------------------------

            if result.response_payload:

                with st.expander(
                    f"{platform_name} "
                    "response details"
                ):

                    st.json(
                        result.response_payload
                    )
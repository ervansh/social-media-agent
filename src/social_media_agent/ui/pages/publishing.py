import streamlit as st

from social_media_agent.config.settings import settings
from social_media_agent.persistence.run_status import RunStatus
from social_media_agent.ui.dependencies import (
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

- **X** — text publishing architecture available
- **Instagram** — requires generated media
- **YouTube** — requires a final video file
"""
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
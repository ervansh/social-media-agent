import streamlit as st

from social_media_agent.ui.dependencies import (
    get_persistence_service,
)


def render():

    st.title("Social Media Agent")
    st.subheader("Content Pipeline")

    persistence = (
        get_persistence_service()
    )

    runs = persistence.list_runs(
        limit=100
    )

    if not runs:
        st.info(
            "No content runs found."
        )
        return

    total_runs = len(runs)

    ready_for_review = sum(
        run.status
        == "ready_for_human_review"
        for run in runs
    )

    approved = sum(
        run.status
        == "approved_for_publishing"
        for run in runs
    )

    rejected = sum(
        run.status == "rejected"
        for run in runs
    )

    col1, col2, col3, col4 = st.columns(
        4
    )

    col1.metric(
        "Runs",
        total_runs,
    )

    col2.metric(
        "Awaiting Review",
        ready_for_review,
    )

    col3.metric(
        "Approved",
        approved,
    )

    col4.metric(
        "Rejected",
        rejected,
    )

    st.divider()

    st.subheader("Recent Runs")

    data = []

    for run in runs:

        data.append(
            {
                "Run ID": run.id,
                "Topic": run.topic,
                "Audience": run.audience,
                "Status": run.status,
                "Created": run.created_at,
            }
        )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True,
    )
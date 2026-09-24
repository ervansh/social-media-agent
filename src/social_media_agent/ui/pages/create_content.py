import streamlit as st

from social_media_agent.models.content_idea import (
    IdeaBatch,
)
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)
from social_media_agent.ui.dependencies import (
    get_content_pipeline_service,
    get_persistence_service,
)


def render():

    st.title("Create Content")

    pipeline = (
        get_content_pipeline_service()
    )

    persistence = (
        get_persistence_service()
    )

    # =============================================
    # New content run
    # =============================================

    st.subheader("1. Research & Generate Ideas")

    with st.form(
        "new_content_form"
    ):

        topic = st.text_input(
            "Topic",
            placeholder=(
                "Example: AI automation testing"
            ),
        )

        audience = st.text_input(
            "Target Audience",
            placeholder=(
                "Example: Software testers "
                "and QA engineers"
            ),
        )

        submitted = (
            st.form_submit_button(
                "Generate Ideas",
                type="primary",
            )
        )

    if submitted:

        topic = topic.strip()
        audience = audience.strip()

        if not topic:
            st.error(
                "Topic is required."
            )
            return

        if not audience:
            st.error(
                "Target audience is required."
            )
            return

        try:

            with st.spinner(
                "Researching and generating ideas..."
            ):

                run_id, _ = (
                    pipeline.generate_ideas(
                        topic=topic,
                        audience=audience,
                    )
                )

            # UI pointer only.
            # Database remains source of truth.
            st.session_state[
                "active_run_id"
            ] = run_id

            st.success(
                "Ideas generated successfully."
            )

            st.rerun()

        except Exception as exc:

            st.error(
                f"Generation failed: {exc}"
            )

            return

    # =============================================
    # Allow existing pending run to be resumed
    # =============================================

    pending_runs = [
        run
        for run in persistence.list_runs(
            limit=100
        )
        if run.status
        == RunStatus.AWAITING_IDEA_APPROVAL.value
    ]

    if pending_runs:

        st.divider()

        st.subheader(
            "Resume Pending Run"
        )

        pending_map = {
            run.id: run
            for run in pending_runs
        }

        resume_run_id = st.selectbox(
            "Pending run",
            options=list(
                pending_map.keys()
            ),
            format_func=lambda run_id: (
                pending_map[run_id].topic
                + " — "
                + pending_map[
                    run_id
                ].audience
            ),
        )

        if st.button(
            "Load Run"
        ):
            st.session_state[
                "active_run_id"
            ] = resume_run_id

            st.rerun()

    # =============================================
    # Idea approval
    # =============================================

    run_id = st.session_state.get(
        "active_run_id"
    )

    if not run_id:
        return

    run = persistence.get_run(
        run_id
    )

    if run is None:
        st.session_state.pop(
            "active_run_id",
            None,
        )
        return

    ideas_payload = (
        persistence.get_latest_payload(
            run_id,
            ArtifactType.IDEAS,
        )
    )

    if ideas_payload is None:
        return

    ideas = IdeaBatch.model_validate(
        ideas_payload
    )

    st.divider()

    st.subheader(
        "2. Select & Approve Idea"
    )

    st.caption(
        f"Run ID: {run_id}"
    )

    idea_options = list(
        range(
            len(ideas.ideas)
        )
    )

    selected_index = st.radio(
        "Select an idea",
        options=idea_options,
        format_func=lambda index: (
            ideas.ideas[index].title
        ),
    )

    selected_idea = ideas.ideas[
        selected_index
    ]

    with st.container(
        border=True
    ):

        st.markdown(
            f"### {selected_idea.title}"
        )

        st.write(
            f"**Hook:** "
            f"{selected_idea.hook}"
        )

        st.write(
            f"**Angle:** "
            f"{selected_idea.angle}"
        )

        st.write(
            "**Platforms:** "
            + ", ".join(
                selected_idea
                .recommended_platforms
            )
        )

        st.write(
            f"**Rationale:** "
            f"{selected_idea.rationale}"
        )

    # Only allow generation while waiting for idea approval.

    if (
        run.status
        == RunStatus.AWAITING_IDEA_APPROVAL.value
    ):

        if st.button(
            "Approve Idea & Generate Content",
            type="primary",
            use_container_width=True,
        ):

            try:

                with st.spinner(
                    "Generating strategy, "
                    "master content, platform "
                    "content and quality review..."
                ):

                    final_status = (
                        pipeline.generate_content(
                            run_id=run_id,
                            idea_index=selected_index,
                        )
                    )

                if (
                    final_status
                    == RunStatus
                    .READY_FOR_HUMAN_REVIEW
                    .value
                ):

                    st.success(
                        "Content generated and "
                        "passed quality checks."
                    )

                    st.info(
                        "Open Content Review "
                        "to inspect and approve "
                        "the generated content."
                    )

                else:

                    st.warning(
                        "Pipeline completed with "
                        f"status: {final_status}"
                    )

                # Finished run no longer needs
                # to remain active in the UI.

                st.session_state.pop(
                    "active_run_id",
                    None,
                )

            except Exception as exc:

                st.error(
                    f"Content generation failed: "
                    f"{exc}"
                )
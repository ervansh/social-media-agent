from langgraph.graph import END, START, StateGraph

from social_media_agent.config.settings import settings
from social_media_agent.models.quality_state import QualityState


def build_quality_workflow(
    quality_agent,
    youtube_agent,
    instagram_agent,
    x_agent,
):

    # ==========================================================
    # Quality Review
    # ==========================================================

    def review_node(
        state: QualityState,
    ) -> dict:

        report = quality_agent.run(
            strategy=state["strategy"],
            master_content=state["master_content"],

            # IMPORTANT:
            # Platforms are optional.
            youtube=state.get("youtube"),
            instagram=state.get("instagram"),
            x=state.get("x"),
        )

        return {
            "quality_report": report,
        }

    # ==========================================================
    # Decide what happens after review
    # ==========================================================

    def route_after_review(
        state: QualityState,
    ) -> str:

        report = state["quality_report"]

        # ---------------------------------------------
        # Quality passed
        # ---------------------------------------------

        if report.passed:
            return "passed"

        retry_count = state.get(
            "retry_count",
            0,
        )

        # ---------------------------------------------
        # Retry exhausted
        # ---------------------------------------------

        if (
            retry_count
            >= settings.max_quality_retries
        ):
            return "failed"

        # ---------------------------------------------
        # Regenerate affected platforms
        # ---------------------------------------------

        return "revise"

    # ==========================================================
    # Revise platform content
    # ==========================================================

    def revise_node(
        state: QualityState,
    ) -> dict:

        report = state["quality_report"]

        # Only ERROR issues cause regeneration.
        error_issues = [
            issue
            for issue in report.issues
            if issue.severity == "error"
        ]

        error_platforms = {
            issue.platform
            for issue in error_issues
        }

        # ---------------------------------------------
        # "general" means all generated platforms
        # should be considered for regeneration.
        # ---------------------------------------------

        regenerate_all = (
            "general" in error_platforms
        )

        updates: dict = {}

        # ---------------------------------------------
        # Build feedback helper
        # ---------------------------------------------

        def feedback_for(
            platform: str,
        ) -> str:

            messages = []

            for issue in error_issues:

                if (
                    issue.platform == platform
                    or issue.platform == "general"
                ):
                    messages.append(
                        issue.message
                    )

            return "\n".join(messages)

        # ==================================================
        # YouTube
        # ==================================================

        current_youtube = state.get(
            "youtube"
        )

        if (
            current_youtube is not None
            and (
                regenerate_all
                or "youtube" in error_platforms
            )
        ):

            updates["youtube"] = (
                youtube_agent.run(
                    strategy=state["strategy"],
                    master_content=state[
                        "master_content"
                    ],
                    feedback=feedback_for(
                        "youtube"
                    ),
                )
            )

        # ==================================================
        # Instagram
        # ==================================================

        current_instagram = state.get(
            "instagram"
        )

        if (
            current_instagram is not None
            and (
                regenerate_all
                or "instagram" in error_platforms
            )
        ):

            updates["instagram"] = (
                instagram_agent.run(
                    strategy=state["strategy"],
                    master_content=state[
                        "master_content"
                    ],
                    feedback=feedback_for(
                        "instagram"
                    ),
                )
            )

        # ==================================================
        # X
        # ==================================================

        current_x = state.get(
            "x"
        )

        if (
            current_x is not None
            and (
                regenerate_all
                or "x" in error_platforms
            )
        ):

            updates["x"] = (
                x_agent.run(
                    strategy=state["strategy"],
                    master_content=state[
                        "master_content"
                    ],
                    feedback=feedback_for(
                        "x"
                    ),
                )
            )

        # ---------------------------------------------
        # Increment retry count
        # ---------------------------------------------

        updates["retry_count"] = (
            state.get(
                "retry_count",
                0,
            )
            + 1
        )

        return updates

    # ==========================================================
    # Failed Quality Gate
    # ==========================================================

    def failed_node(
        state: QualityState,
    ) -> dict:

        return {
            "quality_status":
                "failed",
        }

    # ==========================================================
    # Passed Quality Gate
    # ==========================================================

    def passed_node(
        state: QualityState,
    ) -> dict:

        return {
            "quality_status":
                "passed",
        }

    # ==========================================================
    # Graph
    # ==========================================================

    graph = StateGraph(
        QualityState
    )

    graph.add_node(
        "review",
        review_node,
    )

    graph.add_node(
        "revise",
        revise_node,
    )

    graph.add_node(
        "passed",
        passed_node,
    )

    graph.add_node(
        "failed",
        failed_node,
    )

    # ---------------------------------------------
    # Start
    # ---------------------------------------------

    graph.add_edge(
        START,
        "review",
    )

    # ---------------------------------------------
    # Quality decision
    # ---------------------------------------------

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "passed": "passed",
            "revise": "revise",
            "failed": "failed",
        },
    )

    # ---------------------------------------------
    # Retry after regeneration
    # ---------------------------------------------

    graph.add_edge(
        "revise",
        "review",
    )

    # ---------------------------------------------
    # Finish
    # ---------------------------------------------

    graph.add_edge(
        "passed",
        END,
    )

    graph.add_edge(
        "failed",
        END,
    )

    return graph.compile()
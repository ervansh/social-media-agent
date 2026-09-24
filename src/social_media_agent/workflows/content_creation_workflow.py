from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.content_creation_state import (
    ContentCreationState,
)


def build_content_creation_workflow(
    strategy_agent,
    master_content_agent,
    grounding_agent,
):

    # ======================================================
    # Strategy
    # ======================================================

    def strategy_node(
        state: ContentCreationState,
    ) -> dict:

        strategy = strategy_agent.run(
            research=state["research"],
            selected_idea=state[
                "selected_idea"
            ],
        )

        return {
            "strategy": strategy,

            "grounding_retry_count":
                state.get(
                    "grounding_retry_count",
                    0,
                ),
        }

    # ======================================================
    # Master Content
    # ======================================================

    def master_content_node(
        state: ContentCreationState,
    ) -> dict:

        master_content = (
            master_content_agent.run(
                research=state["research"],

                selected_idea=state[
                    "selected_idea"
                ],

                strategy=state[
                    "strategy"
                ],
            )
        )

        return {
            "master_content":
                master_content,
        }

    # ======================================================
    # Grounding Review
    # ======================================================

    def grounding_review_node(
        state: ContentCreationState,
    ) -> dict:

        report = grounding_agent.run(
            research=state["research"],

            master_content=state[
                "master_content"
            ],
        )

        return {
            "grounding_report":
                report,
        }

    # ======================================================
    # Route after Grounding
    # ======================================================

    def route_after_grounding(
        state: ContentCreationState,
    ) -> str:

        report = state[
            "grounding_report"
        ]

        if report.passed:
            return "passed"

        retry_count = state.get(
            "grounding_retry_count",
            0,
        )

        if (
            retry_count
            >= settings.max_grounding_retries
        ):
            return "failed"

        return "revise"

    # ======================================================
    # Revise Master Content
    # ======================================================

    def revise_master_content_node(
        state: ContentCreationState,
    ) -> dict:

        report = state[
            "grounding_report"
        ]

        # ----------------------------------------------
        # Only warnings/errors should be fed back.
        #
        # SUPPORTED findings must NOT cause rewriting.
        # ----------------------------------------------

        actionable_issues = [
            issue
            for issue in report.issues
            if issue.severity
            in {
                "warning",
                "error",
            }
        ]

        feedback_lines = []

        for issue in actionable_issues:

            feedback_lines.append(
                (
                    f"[{issue.severity.upper()}]\n"
                    f"Claim: {issue.claim}\n"
                    f"Reason: {issue.reason}"
                )
            )

        feedback = "\n\n".join(
            feedback_lines
        )

        master_content = (
            master_content_agent.run(
                research=state["research"],

                selected_idea=state[
                    "selected_idea"
                ],

                strategy=state[
                    "strategy"
                ],

                feedback=feedback,
                previous_master_content=state[
                    "master_content"
                ],
            )
        )

        retry_count = (
            state.get(
                "grounding_retry_count",
                0,
            )
            + 1
        )

        return {
            "master_content":
                master_content,

            "grounding_retry_count":
                retry_count,
        }

    # ======================================================
    # Grounding Passed
    # ======================================================

    def grounding_passed_node(
        state: ContentCreationState,
    ) -> dict:

        return {
            "grounding_status":
                "passed",

            "review_status":
                "pending",
        }

    # ======================================================
    # Grounding Failed
    # ======================================================

    def grounding_failed_node(
        state: ContentCreationState,
    ) -> dict:

        return {
            "grounding_status":
                "failed",

            "review_status":
                "failed_grounding",
        }

    # ======================================================
    # Graph
    # ======================================================

    graph = StateGraph(
        ContentCreationState
    )

    graph.add_node(
        "strategy",
        strategy_node,
    )

    graph.add_node(
        "master_content",
        master_content_node,
    )

    graph.add_node(
        "grounding_review",
        grounding_review_node,
    )

    graph.add_node(
        "revise_master_content",
        revise_master_content_node,
    )

    graph.add_node(
        "grounding_passed",
        grounding_passed_node,
    )

    graph.add_node(
        "grounding_failed",
        grounding_failed_node,
    )

    # ======================================================
    # Flow
    # ======================================================

    graph.add_edge(
        START,
        "strategy",
    )

    graph.add_edge(
        "strategy",
        "master_content",
    )

    graph.add_edge(
        "master_content",
        "grounding_review",
    )

    graph.add_conditional_edges(
        "grounding_review",
        route_after_grounding,
        {
            "passed":
                "grounding_passed",

            "revise":
                "revise_master_content",

            "failed":
                "grounding_failed",
        },
    )

    graph.add_edge(
        "revise_master_content",
        "grounding_review",
    )

    graph.add_edge(
        "grounding_passed",
        END,
    )

    graph.add_edge(
        "grounding_failed",
        END,
    )

    return graph.compile()
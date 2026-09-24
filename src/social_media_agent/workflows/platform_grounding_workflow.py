from typing import TypedDict

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from social_media_agent.config.settings import (
    settings,
)
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.platform_grounding import (
    PlatformGroundingBatch,
)


class PlatformGroundingState(
    TypedDict,
    total=False,
):
    strategy: ContentStrategy

    master_content: MasterContent

    youtube: YouTubePackage

    instagram: InstagramPackage

    x: XPackage

    platform_grounding_report: (
        PlatformGroundingBatch
    )

    retry_count: int

    platform_grounding_status: str


def build_platform_grounding_workflow(
    *,
    grounding_agent,
    youtube_agent,
    instagram_agent,
    x_agent,
):

    # ======================================================
    # Review
    # ======================================================

    def review_node(
        state: PlatformGroundingState,
    ) -> dict:

        reports = []

        youtube = state.get(
            "youtube"
        )

        instagram = state.get(
            "instagram"
        )

        x_content = state.get(
            "x"
        )

        if youtube is not None:

            reports.append(
                grounding_agent.run(
                    master_content=state[
                        "master_content"
                    ],
                    platform="youtube",
                    platform_content=youtube,
                )
            )

        if instagram is not None:

            reports.append(
                grounding_agent.run(
                    master_content=state[
                        "master_content"
                    ],
                    platform="instagram",
                    platform_content=instagram,
                )
            )

        if x_content is not None:

            reports.append(
                grounding_agent.run(
                    master_content=state[
                        "master_content"
                    ],
                    platform="x",
                    platform_content=x_content,
                )
            )

        passed = all(
            report.passed
            for report in reports
        )

        return {
            "platform_grounding_report":
                PlatformGroundingBatch(
                    passed=passed,
                    reports=reports,
                ),

            "retry_count":
                state.get(
                    "retry_count",
                    0,
                ),
        }

    # ======================================================
    # Route
    # ======================================================

    def route_after_review(
        state: PlatformGroundingState,
    ) -> str:

        report = state[
            "platform_grounding_report"
        ]

        if report.passed:
            return "passed"

        retry_count = state.get(
            "retry_count",
            0,
        )

        if (
            retry_count
            >= settings
            .max_platform_grounding_retries
        ):
            return "failed"

        return "revise"

    # ======================================================
    # Build revision feedback
    # ======================================================

    def build_feedback(
        batch: PlatformGroundingBatch,
        platform: str,
    ) -> str:

        platform_report = next(
            (
                report
                for report
                in batch.reports
                if report.platform
                == platform
            ),
            None,
        )

        if platform_report is None:
            return ""

        actionable = [
            issue
            for issue
            in platform_report.issues
            if issue.severity
            in {
                "warning",
                "error",
            }
        ]

        if not actionable:
            return ""

        issue_blocks = []

        for issue in actionable:

            issue_blocks.append(
                "\n".join(
                    [
                        (
                            "["
                            f"{issue.severity.upper()}"
                            "]"
                        ),
                        (
                            "Claim: "
                            f"{issue.claim}"
                        ),
                        (
                            "Reason: "
                            f"{issue.reason}"
                        ),
                    ]
                )
            )

        issues_text = "\n\n".join(
            issue_blocks
        )

        return f"""
PLATFORM GROUNDING REVISION REQUIRED.

MASTER CONTENT is the factual ceiling.

ERROR issues are mandatory corrections.

WARNING issues should be corrected where possible.

Do not preserve a factual statement because it
appeared in:

- an earlier strategy,
- an idea,
- research,
- a previous platform draft.

If an issue says a statement is too broad:

remove it or narrow it to MASTER CONTENT.

If an issue identifies incorrect attribution:

remove that attribution unless MASTER CONTENT
explicitly supports it.

Do not fix unsupported content by surrounding it
with disclaimers.

Do not introduce replacement factual claims.

ISSUES:

{issues_text}
"""

    # ======================================================
    # Revision
    # ======================================================

    def revise_node(
        state: PlatformGroundingState,
    ) -> dict:

        batch = state[
            "platform_grounding_report"
        ]

        # Only platforms containing ERRORs fail
        # because PlatformGroundingReport.passed is
        # deterministic from ERROR presence.

        failing_platforms = {
            report.platform
            for report
            in batch.reports
            if not report.passed
        }

        updates = {}

        if (
            "youtube"
            in failing_platforms
            and state.get(
                "youtube"
            )
            is not None
        ):

            feedback = build_feedback(
                batch,
                "youtube",
            )

            updates[
                "youtube"
            ] = youtube_agent.run(
                strategy=state[
                    "strategy"
                ],
                master_content=state[
                    "master_content"
                ],
                feedback=feedback,
            )

        if (
            "instagram"
            in failing_platforms
            and state.get(
                "instagram"
            )
            is not None
        ):

            feedback = build_feedback(
                batch,
                "instagram",
            )

            updates[
                "instagram"
            ] = instagram_agent.run(
                strategy=state[
                    "strategy"
                ],
                master_content=state[
                    "master_content"
                ],
                feedback=feedback,
            )

        if (
            "x"
            in failing_platforms
            and state.get(
                "x"
            )
            is not None
        ):

            feedback = build_feedback(
                batch,
                "x",
            )

            updates[
                "x"
            ] = x_agent.run(
                strategy=state[
                    "strategy"
                ],
                master_content=state[
                    "master_content"
                ],
                feedback=feedback,
            )

        updates[
            "retry_count"
        ] = (
            state.get(
                "retry_count",
                0,
            )
            + 1
        )

        return updates

    # ======================================================
    # Result nodes
    # ======================================================

    def passed_node(
        state: PlatformGroundingState,
    ) -> dict:

        return {
            "platform_grounding_status":
                "passed",
        }

    def failed_node(
        state: PlatformGroundingState,
    ) -> dict:

        return {
            "platform_grounding_status":
                "failed",
        }

    # ======================================================
    # Graph
    # ======================================================

    graph = StateGraph(
        PlatformGroundingState
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

    graph.add_edge(
        START,
        "review",
    )

    graph.add_conditional_edges(
        "review",
        route_after_review,
        {
            "passed":
                "passed",

            "revise":
                "revise",

            "failed":
                "failed",
        },
    )

    graph.add_edge(
        "revise",
        "review",
    )

    graph.add_edge(
        "passed",
        END,
    )

    graph.add_edge(
        "failed",
        END,
    )

    return graph.compile()
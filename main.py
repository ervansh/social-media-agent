import argparse

from social_media_agent.config.settings import settings
from social_media_agent.core.logger import configure_logging
from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.database import (
    SessionFactory,
    initialize_database,
)
from social_media_agent.persistence.repository import (
    ContentRepository,
)
from social_media_agent.persistence.service import (
    PersistenceService,
)

from social_media_agent.services.image.factory import (
    get_image_provider,
)
from social_media_agent.services.image_generation.creative_image_service import (
    CreativeImageGenerationService,
)
from social_media_agent.services.llm.factory import (
    get_llm_provider,
)
from social_media_agent.services.pipeline.content_pipeline_service import (
    ContentPipelineService,
)
from social_media_agent.services.search.factory import (
    get_search_provider,
)

logger = configure_logging()


# ==========================================================
# CLI Arguments
# ==========================================================


def parse_arguments():

    parser = argparse.ArgumentParser(
        description=("Agentic Social Media Content System")
    )

    parser.add_argument(
        "--topic",
        required=False,
        help="Topic for a new content run",
    )

    parser.add_argument(
        "--audience",
        required=False,
        help="Target audience for a new run",
    )

    parser.add_argument(
        "--run-id",
        required=False,
        help="Resume an existing content run",
    )

    args = parser.parse_args()

    # ==================================================
    # Resume mode
    # ==================================================

    if args.run_id:

        if args.topic is not None or args.audience is not None:
            parser.error("--run-id cannot be combined " "with --topic or --audience.")

        return args

    # ==================================================
    # New-run mode
    # ==================================================

    if not args.topic:
        parser.error("--topic is required for a new run.")

    if not args.audience:
        parser.error("--audience is required for a new run.")

    return args


# ==========================================================
# Optional Image Generation
# ==========================================================


def create_image_generation_service():

    if not settings.image_generation_enabled:
        return None

    provider = get_image_provider()

    return CreativeImageGenerationService(
        provider=provider,
    )


# ==========================================================
# Idea Display
# ==========================================================


def print_ideas(ideas):

    print("\nCONTENT IDEAS")
    print("-------------")

    for index, idea in enumerate(
        ideas,
        start=1,
    ):

        print(f"\n{index}. {idea.title}")

        print(f"   Hook      : {idea.hook}")

        print(f"   Angle     : {idea.angle}")

        print("   Platforms : " + ", ".join(idea.recommended_platforms))

        print(f"   Rationale : " f"{idea.rationale}")


# ==========================================================
# Human Idea Selection
# ==========================================================


def select_idea(
    ideas,
):

    while True:

        selection = input("\nSelect idea number to approve " "(or 0 to exit): ")

        try:
            selected_index = int(selection)

        except ValueError:

            print("Please enter a valid number.")

            continue

        if selected_index == 0:
            return None

        if 1 <= selected_index <= len(ideas):

            # Pipeline expects zero-based index.
            return selected_index - 1

        print("Selection is outside " "the available range.")


def print_platform_grounding_report(
    persistence,
    run_id: str,
) -> None:

    payload = persistence.get_latest_payload(
        run_id,
        ArtifactType.PLATFORM_GROUNDING_REPORT,
    )

    if payload is None:
        return

    print()
    print("PLATFORM GROUNDING REPORT")
    print("-------------------------")

    passed = payload.get(
        "passed",
        False,
    )

    print(f"Status: " f"{'PASSED' if passed else 'FAILED'}")

    reports = payload.get(
        "reports",
        [],
    )

    for report in reports:

        platform = report.get(
            "platform",
            "unknown",
        )

        platform_passed = report.get(
            "passed",
            False,
        )

        print()
        print(platform.upper())
        print(f"Status: " f"{'PASSED' if platform_passed else 'FAILED'}")

        summary = report.get("summary")

        if summary:
            print(summary)

        issues = report.get(
            "issues",
            [],
        )

        if not issues:
            continue

        print()
        print("Issues:")

        for issue in issues:

            severity = issue.get("severity", "").upper()

            claim = issue.get("claim", "")

            reason = issue.get("reason", "")

            print(f"- [{severity}] {claim}")

            if reason:
                print(f"  Reason: {reason}")

            urls = issue.get(
                "supporting_source_urls",
                [],
            )

            if urls:

                print("  Sources:")

                for url in urls:
                    print(f"    - {url}")


# ==========================================================
# Display Final Output
# ==========================================================


def print_final_output(
    persistence,
    run_id,
):
    run = persistence.get_run(run_id)

    if run is None:
        raise ValueError(f"Run not found: {run_id}")

    current_status = str(
        getattr(run.status, "value", run.status)
    ).upper()
    # ------------------------------------------------------
    # Selected Idea
    # ------------------------------------------------------

    selected_idea = persistence.get_latest_payload(
        run_id,
        ArtifactType.SELECTED_IDEA,
    )

    if selected_idea:

        print("\nSELECTED IDEA")
        print("-------------")

        print(
            selected_idea.get(
                "title",
                "",
            )
        )

        platforms = (
            selected_idea.get(
                "recommended_platforms",
                [],
            )
        )

        if platforms:
            print(
                "Platforms:",
                ", ".join(
                    platforms
                ),
            )

    # ------------------------------------------------------
    # Strategy
    # ------------------------------------------------------

    strategy = persistence.get_latest_payload(
        run_id,
        ArtifactType.STRATEGY,
    )

    if strategy:

        print("\nCONTENT STRATEGY")
        print("----------------")

        print(
            "Objective :",
            strategy.get(
                "objective",
                "",
            ),
        )

        print(
            "Message   :",
            strategy.get(
                "core_message",
                "",
            ),
        )

        print(
            "Tone      :",
            strategy.get(
                "tone",
                "",
            ),
        )

        print(
            "Depth     :",
            strategy.get(
                "content_depth",
                "",
            ),
        )

    # ------------------------------------------------------
    # Master Content
    # ------------------------------------------------------

    master_content = persistence.get_latest_payload(
        run_id,
        ArtifactType.MASTER_CONTENT,
    )

    if master_content:

        print("\nMASTER CONTENT")
        print("--------------")

        print(
            "Title:",
            master_content.get(
                "title",
                "",
            ),
        )

        print(
            "\nHook:",
            master_content.get(
                "hook",
                "",
            ),
        )

        print(
            "\nCore Message:",
            master_content.get(
                "core_message",
                "",
            ),
        )

        sections = master_content.get(
            "sections",
            [],
        )

        if sections:

            print("\nSections:")

            for section in sections:

                print(f"\n{section.get('heading', '')}")

                print(
                    "Purpose:",
                    section.get(
                        "purpose",
                        "",
                    ),
                )

                for point in section.get(
                    "key_points",
                    [],
                ):

                    print(f"  - {point}")

        key_takeaways = master_content.get(
            "key_takeaways",
            [],
        )

        if key_takeaways:

            print("\nKey Takeaways:")

            for takeaway in key_takeaways:
                print(
                    f"  - {takeaway}"
                )

        call_to_action = master_content.get(
            "call_to_action",
            "",
        )

        if call_to_action:

            print(
                "\nCall to Action:",
                call_to_action,
            )

    # ------------------------------------------------------
    # Grounding
    # ------------------------------------------------------

    grounding = persistence.get_latest_payload(
        run_id,
        ArtifactType.GROUNDING_REPORT,
    )

    if grounding:

        print("\nGROUNDING REPORT")
        print("----------------")

        print(
            "Status:",
            ("PASSED" if grounding.get("passed") else "FAILED"),
        )

        print(
            grounding.get(
                "summary",
                "",
            )
        )
        issues = grounding.get(
            "issues",
            [],
        )

        if issues:

            print("\nGrounding Issues:")

            for issue in issues:

                print(
                    f"- "
                    f"[{issue.get('severity', '').upper()}] "
                    f"{issue.get('claim', '')}"
                )

                print(f"  Reason: " f"{issue.get('reason', '')}")

                supporting_urls = issue.get(
                    "supporting_source_urls",
                    [],
                )

                if supporting_urls:

                    print("  Sources:")

                    for url in supporting_urls:

                        print(f"    - {url}")

    # ------------------------------------------------------
    # Platform Content
    # ------------------------------------------------------

    platforms = (
        "youtube",
        "instagram",
        "x",
    )

    for platform in platforms:

        platform_content = persistence.get_latest_payload(
            run_id,
            ArtifactType.PLATFORM_CONTENT,
            platform=platform,
        )

        if platform_content is None:
            continue

        print(f"\n{platform.upper()}")

        print("-" * len(platform))

        if platform == "youtube":

            print(
                "Title:",
                platform_content.get(
                    "title",
                    "",
                ),
            )

            print("\nDescription:")

            print(
                platform_content.get(
                    "description",
                    "",
                )
            )

            print("\nScript:")

            print(
                platform_content.get(
                    "script",
                    "",
                )
            )

        elif platform == "instagram":

            print(
                "Hook:",
                platform_content.get(
                    "reel_hook",
                    "",
                ),
            )

            print("\nReel Script:")

            print(
                platform_content.get(
                    "reel_script",
                    "",
                )
            )

            print("\nCaption:")

            print(
                platform_content.get(
                    "caption",
                    "",
                )
            )

        elif platform == "x":

            print(
                platform_content.get(
                    "single_post",
                    "",
                )
            )

            thread = platform_content.get(
                "thread",
                [],
            )

            if thread:

                print("\nThread:")

                for index, post in enumerate(
                    thread,
                    start=1,
                ):

                    print(f"{index}. {post}")

    # ------------------------------------------------------
    # Platform Grounding Report
    # ------------------------------------------------------

    print_platform_grounding_report(
        persistence=persistence,
        run_id=run_id,
    )

    # ------------------------------------------------------
    # Quality Report
    #
    # Do not display a previously persisted Quality report
    # when the current run failed an upstream grounding gate.
    # ------------------------------------------------------

    quality_is_current = current_status not in {
        "FAILED_GROUNDING",
        "FAILED_PLATFORM_GROUNDING",
    }

    if quality_is_current:

        quality = persistence.get_latest_payload(
            run_id,
            ArtifactType.QUALITY_REPORT,
        )

        if quality:

            print("\nQUALITY REPORT")
            print("--------------")

            print(
                "Status:",
                ("PASSED" if quality.get("passed") else "FAILED"),
            )

            print(
                quality.get(
                    "summary",
                    "",
                )
            )

            for issue in quality.get(
                "issues",
                [],
            ):

                print(
                    f"- "
                    f"[{issue.get('severity', '').upper()}] "
                    f"{issue.get('platform', '')}: "
                    f"{issue.get('message', '')}"
                )

    # ------------------------------------------------------
    # Creative Assets
    #
    # Creative output is stale whenever any upstream gate in
    # the current execution failed.
    # ------------------------------------------------------

    creative_is_current = current_status not in {
        "FAILED_GROUNDING",
        "FAILED_PLATFORM_GROUNDING",
        "FAILED_QUALITY_GATE",
    }

    if creative_is_current:

        creative_assets = persistence.get_latest_payload(
            run_id,
            ArtifactType.CREATIVE_ASSETS,
        )

        if creative_assets:

            images = creative_assets.get(
                "images",
                [],
            )

            storyboards = creative_assets.get(
                "storyboards",
                [],
            )

            print("\nCREATIVE ASSETS")
            print("---------------")

            print(f"Image briefs : {len(images)}")
            print(f"Storyboards  : {len(storyboards)}")


# ==========================================================
# Main
# ==========================================================


def main():

    # ------------------------------------------------------
    # Parse arguments FIRST
    # ------------------------------------------------------

    args = parse_arguments()

    if args.run_id:

        logger.info(
            "Resume requested for run: {}",
            args.run_id,
        )

    else:

        logger.info(
            "Starting workflow for topic: {}",
            args.topic,
        )

    # ------------------------------------------------------
    # Database
    # ------------------------------------------------------

    initialize_database()

    repository = ContentRepository(SessionFactory)

    persistence = PersistenceService(repository)

    # ------------------------------------------------------
    # Providers
    # ------------------------------------------------------

    llm = get_llm_provider()

    search_provider = get_search_provider()

    image_generation_service = create_image_generation_service()

    # ------------------------------------------------------
    # Main Pipeline Service
    # ------------------------------------------------------

    pipeline = ContentPipelineService(
        llm=llm,
        search_provider=search_provider,
        persistence=persistence,
        image_generation_service=(image_generation_service),
    )

    # ======================================================
    # RESUME MODE
    # ======================================================

    if args.run_id:

        logger.info(
            "Resuming existing run: {}",
            args.run_id,
        )

        try:

            final_status = pipeline.resume_run(run_id=args.run_id)

        except Exception:

            logger.exception(
                "Resume failed for run: {}",
                args.run_id,
            )

            raise

        print_final_output(
            persistence=persistence,
            run_id=args.run_id,
        )

        print("\nFINAL RUN STATUS")

        print("----------------")

        print(final_status.upper())

        return

    # ======================================================
    # PHASE 2
    # Research + Idea Generation
    # ======================================================

    try:

        run_id, idea_batch = pipeline.generate_ideas(
            topic=args.topic,
            audience=args.audience,
        )

    except Exception:

        logger.exception("Idea generation failed.")

        raise

    logger.info(
        "Content run created: {}",
        run_id,
    )

    print(f"\nRun ID: {run_id}")

    # ------------------------------------------------------
    # Research Summary
    # ------------------------------------------------------

    research = persistence.get_latest_payload(
        run_id,
        ArtifactType.RESEARCH,
    )

    if research:

        print("\nRESEARCH SUMMARY")
        print("----------------")

        print(
            research.get(
                "summary",
                "",
            )
        )

    # ------------------------------------------------------
    # Ideas
    # ------------------------------------------------------

    print_ideas(idea_batch.ideas)

    print("\nStatus: " "AWAITING IDEA APPROVAL")

    # ======================================================
    # Human Approval
    # ======================================================

    selected_index = select_idea(idea_batch.ideas)

    if selected_index is None:

        logger.info("Workflow stopped: " "no idea selected.")

        print("\nNo idea selected.")

        return

    selected_idea = idea_batch.ideas[selected_index]

    logger.info(
        "Idea approved: {}",
        selected_idea.title,
    )

    # ======================================================
    # PHASE 3 → 8
    # Strategy
    # Master Content
    # Grounding
    # Platform Content
    # Quality
    # Creative Assets
    # Optional Images
    # ======================================================

    try:

        final_status = pipeline.generate_content(
            run_id=run_id,
            idea_index=selected_index,
        )

    except Exception:

        logger.exception(
            "Content generation failed " "for run: {}",
            run_id,
        )

        raise

    # ======================================================
    # Final Output
    # ======================================================

    print_final_output(
        persistence=persistence,
        run_id=run_id,
    )

    print("\nFINAL RUN STATUS")

    print("----------------")

    print(final_status.upper())

    logger.info(
        "Workflow completed with " "status: {}",
        final_status,
    )


# ==========================================================
# Application Entry Point
# ==========================================================


if __name__ == "__main__":
    main()
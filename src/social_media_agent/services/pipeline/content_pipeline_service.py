from social_media_agent.agents.platform_grounding_agent import (
    PlatformGroundingAgent,
)

from social_media_agent.workflows.platform_grounding_workflow import (
    build_platform_grounding_workflow,
)
from social_media_agent.agents.creative_agent import (
    CreativeAgent,
)
from social_media_agent.agents.grounding_review_agent import (
    GroundingReviewAgent,
)
from social_media_agent.agents.idea_agent import (
    IdeaAgent,
)
from social_media_agent.agents.instagram_agent import (
    InstagramAgent,
)
from social_media_agent.agents.master_content_agent import (
    MasterContentAgent,
)
from social_media_agent.agents.quality_review_agent import (
    QualityReviewAgent,
)
from social_media_agent.agents.research_agent import (
    ResearchAgent,
)
from social_media_agent.agents.strategy_agent import (
    StrategyAgent,
)
from social_media_agent.agents.x_agent import (
    XAgent,
)
from social_media_agent.agents.youtube_agent import (
    YouTubeAgent,
)

from social_media_agent.models.content_idea import (
    IdeaBatch,
)
from social_media_agent.models.research import (
    ResearchBrief,
)

from social_media_agent.persistence.artifact_types import (
    ArtifactType,
)
from social_media_agent.persistence.run_status import (
    RunStatus,
)

from social_media_agent.services.quality.platform_validator import (
    PlatformValidator,
)
from social_media_agent.services.grounding.master_grounding_remediator import (
    MasterGroundingRemediator,
)

from social_media_agent.workflows.content_creation_workflow import (
    build_content_creation_workflow,
)
from social_media_agent.workflows.creative_workflow import (
    build_creative_workflow,
)
from social_media_agent.workflows.ideation_workflow import (
    build_ideation_workflow,
)
from social_media_agent.workflows.platform_content_workflow import (
    build_platform_content_workflow,
)
from social_media_agent.workflows.quality_workflow import (
    build_quality_workflow,
)
from social_media_agent.config.settings import settings

from social_media_agent.models.content_idea import ContentIdea
from social_media_agent.models.content_strategy import ContentStrategy
from social_media_agent.models.creative_assets import CreativeAssetBundle
from social_media_agent.models.grounding import GroundingReport
from social_media_agent.models.master_content import MasterContent
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.quality import QualityReport
from social_media_agent.models.research import ResearchBrief


class ContentPipelineService:

    def __init__(
        self,
        llm,
        search_provider,
        persistence,
        image_generation_service=None,
    ):
        self.llm = llm
        self.search_provider = search_provider
        self.persistence = persistence

        self.image_generation_service = image_generation_service

    # ==================================================
    # PHASE 2
    # Research + Idea Generation
    # ==================================================

    def generate_ideas(
        self,
        topic: str,
        audience: str,
    ) -> tuple[str, IdeaBatch]:

        # ----------------------------------------------
        # Create persistent content run
        # ----------------------------------------------

        run_id = self.persistence.start_run(
            topic=topic,
            audience=audience,
        )

        # ----------------------------------------------
        # Agents
        # ----------------------------------------------

        research_agent = ResearchAgent(
            llm=self.llm,
            search_provider=self.search_provider,
        )

        idea_agent = IdeaAgent(
            llm=self.llm,
        )

        # ----------------------------------------------
        # Workflow
        # ----------------------------------------------

        workflow = build_ideation_workflow(
            research_agent=research_agent,
            idea_agent=idea_agent,
        )

        result = workflow.invoke(
            {
                "topic": topic,
                "audience": audience,
            }
        )

        research = result["research"]
        ideas = result["ideas"]

        # ----------------------------------------------
        # Persist artifacts
        # ----------------------------------------------

        self.persistence.save_model(
            run_id,
            ArtifactType.RESEARCH,
            research,
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.IDEAS,
            ideas,
        )

        self.persistence.update_status(
            run_id,
            RunStatus.AWAITING_IDEA_APPROVAL.value,
        )

        return run_id, ideas

    # ==================================================
    # PHASE 3 - 8
    # Approved Idea → Final Content + Creative Assets
    # ==================================================

    def generate_content(
        self,
        run_id: str,
        idea_index: int,
    ) -> str:

        # ==================================================
        # Load persisted Phase-2 data
        # ==================================================

        research_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.RESEARCH,
        )

        ideas_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.IDEAS,
        )

        if research_payload is None:
            raise ValueError("Research artifact not found.")

        if ideas_payload is None:
            raise ValueError("Ideas artifact not found.")

        research = ResearchBrief.model_validate(research_payload)

        ideas = IdeaBatch.model_validate(ideas_payload)

        if not (0 <= idea_index < len(ideas.ideas)):
            raise ValueError("Invalid idea selection.")

        selected_idea = ideas.ideas[idea_index]

        # ----------------------------------------------
        # Persist approved idea
        # ----------------------------------------------

        self.persistence.save_model(
            run_id,
            ArtifactType.SELECTED_IDEA,
            selected_idea,
        )

        self.persistence.update_status(
            run_id,
            RunStatus.IDEA_APPROVED.value,
        )

        # ==================================================
        # PHASE 3
        # Strategy + Master Content
        # ==================================================

        strategy_agent = StrategyAgent(
            llm=self.llm,
        )

        master_content_agent = MasterContentAgent(
            llm=self.llm,
        )

        grounding_agent = GroundingReviewAgent(
            llm=self.llm,
        )

        content_workflow = build_content_creation_workflow(
            strategy_agent=strategy_agent,
            master_content_agent=(master_content_agent),
            grounding_agent=grounding_agent,
        )

        content_result = content_workflow.invoke(
            {
                "research": research,
                "selected_idea": selected_idea,
            }
        )

        strategy = content_result["strategy"]

        master_content = content_result["master_content"]

        grounding_report = content_result["grounding_report"]

        # ----------------------------------------------
        # Persist Phase-3 artifacts
        # ----------------------------------------------

        self.persistence.save_model(
            run_id,
            ArtifactType.STRATEGY,
            strategy,
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.MASTER_CONTENT,
            master_content,
        )

        self.persistence.save_model(
            run_id,
            ArtifactType.GROUNDING_REPORT,
            grounding_report,
        )

        # ----------------------------------------------
        # Stop pipeline if grounding fails
        # ----------------------------------------------

        if not grounding_report.passed:

            status = RunStatus.FAILED_GROUNDING.value

            self.persistence.update_status(
                run_id,
                status,
            )

            return status

        self.persistence.update_status(
            run_id,
            RunStatus.MASTER_CONTENT_READY.value,
        )

        # ==================================================
        # PHASE 4
        # Platform Content Generation
        # ==================================================

        youtube_agent = YouTubeAgent(
            llm=self.llm,
        )

        instagram_agent = InstagramAgent(
            llm=self.llm,
        )

        x_agent = XAgent(
            llm=self.llm,
        )

        platform_workflow = build_platform_content_workflow(
            youtube_agent=youtube_agent,
            instagram_agent=instagram_agent,
            x_agent=x_agent,
        )

        platform_result = platform_workflow.invoke(
            {
                "strategy": strategy,
                "master_content": master_content,
                "platforms": selected_idea.recommended_platforms,
            }
        )

        youtube = platform_result.get("youtube")

        instagram = platform_result.get("instagram")

        x_content = platform_result.get("x")

        # ----------------------------------------------
        # Persist initial platform versions
        # ----------------------------------------------

        if youtube is not None:

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                youtube,
                platform="youtube",
            )

        if instagram is not None:

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                instagram,
                platform="instagram",
            )

        if x_content is not None:

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                x_content,
                platform="x",
            )

        self.persistence.update_status(
            run_id,
            RunStatus.PLATFORM_CONTENT_GENERATED.value,
        )

        # ==================================================
        # PLATFORM GROUNDING
        # ==================================================

        platform_grounding_agent = (
            PlatformGroundingAgent(
                llm=self.llm
            )
        )

        platform_grounding_workflow = (
            build_platform_grounding_workflow(
                grounding_agent=(
                    platform_grounding_agent
                ),
                youtube_agent=youtube_agent,
                instagram_agent=instagram_agent,
                x_agent=x_agent,
            )
        )

        platform_grounding_input = {
            # "research": research,
            "strategy": strategy,
            "master_content": master_content,
            "retry_count": 0,
        }

        if youtube is not None:
            platform_grounding_input[
                "youtube"
            ] = youtube

        if instagram is not None:
            platform_grounding_input[
                "instagram"
            ] = instagram

        if x_content is not None:
            platform_grounding_input[
                "x"
            ] = x_content


        # Keep originals so we can detect revisions.

        original_youtube = youtube

        original_instagram = instagram

        original_x = x_content


        platform_grounding_result = (
            platform_grounding_workflow.invoke(
                platform_grounding_input
            )
        )


        platform_grounding_report = (
            platform_grounding_result[
                "platform_grounding_report"
            ]
        )


        youtube = (
            platform_grounding_result.get(
                "youtube"
            )
        )

        instagram = (
            platform_grounding_result.get(
                "instagram"
            )
        )

        x_content = (
            platform_grounding_result.get(
                "x"
            )
        )


        # ==================================================
        # Persist revised platform versions
        # ==================================================

        platform_grounding_changed = False


        if (
            youtube is not None
            and (
                original_youtube is None
                or youtube.model_dump()
                != original_youtube.model_dump()
            )
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                youtube,
                platform="youtube",
            )

            platform_grounding_changed = True


        if (
            instagram is not None
            and (
                original_instagram is None
                or instagram.model_dump()
                != original_instagram.model_dump()
            )
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                instagram,
                platform="instagram",
            )

            platform_grounding_changed = True


        if (
            x_content is not None
            and (
                original_x is None
                or x_content.model_dump()
                != original_x.model_dump()
            )
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                x_content,
                platform="x",
            )

            platform_grounding_changed = True


        self.persistence.save_model(
            run_id,
            ArtifactType.PLATFORM_GROUNDING_REPORT,
            platform_grounding_report,
        )


        # ==================================================
        # Stop if platform grounding failed
        # ==================================================

        if not platform_grounding_report.passed:

            status = (
                RunStatus
                .FAILED_PLATFORM_GROUNDING
                .value
            )

            self.persistence.update_status(
                run_id,
                status,
            )

            return status


        # ==================================================
        # Force downstream regeneration if platform content
        # was corrected.
        # ==================================================

        if platform_grounding_changed:

            platform_changed = True

        # ==================================================
        # PHASE 5
        # Quality Gate
        # ==================================================

        validator = PlatformValidator()

        quality_agent = QualityReviewAgent(
            llm=self.llm,
            validator=validator,
        )

        quality_workflow = build_quality_workflow(
            quality_agent=quality_agent,
            youtube_agent=youtube_agent,
            instagram_agent=instagram_agent,
            x_agent=x_agent,
        )

        quality_input = {
            "strategy": strategy,
            "master_content": master_content,
            "retry_count": 0,
        }

        # ----------------------------------------------
        # Add only generated platforms
        # ----------------------------------------------

        if youtube is not None:
            quality_input["youtube"] = youtube

        if instagram is not None:
            quality_input["instagram"] = instagram

        if x_content is not None:
            quality_input["x"] = x_content

        quality_result = quality_workflow.invoke(quality_input)

        quality_report = quality_result["quality_report"]

        # ----------------------------------------------
        # Final platform packages after any
        # quality-triggered regeneration
        # ----------------------------------------------

        final_youtube = quality_result.get("youtube")

        final_instagram = quality_result.get("instagram")

        final_x = quality_result.get("x")

        # ----------------------------------------------
        # Save regenerated platform versions
        # only when content changed
        # ----------------------------------------------

        quality_content_changed = False

        if final_youtube is not None and (
            youtube is None or (final_youtube.model_dump() != youtube.model_dump())
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                final_youtube,
                platform="youtube",
            )

            quality_content_changed = True

        if final_instagram is not None and (
            instagram is None
            or (final_instagram.model_dump() != instagram.model_dump())
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                final_instagram,
                platform="instagram",
            )

            quality_content_changed = True

        if final_x is not None and (
            x_content is None or (final_x.model_dump() != x_content.model_dump())
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                final_x,
                platform="x",
            )

            quality_content_changed = True

        # ----------------------------------------------
        # Persist quality report
        # ----------------------------------------------

        self.persistence.save_model(
            run_id,
            ArtifactType.QUALITY_REPORT,
            quality_report,
        )

        # ----------------------------------------------
        # IMPORTANT:
        # Creative generation must NOT run when
        # quality validation failed.
        # ----------------------------------------------

        if not quality_report.passed:

            status = RunStatus.FAILED_QUALITY_GATE.value

            self.persistence.update_status(
                run_id,
                status,
            )

            return status

        if quality_content_changed:

            post_quality_input = {
                "strategy": strategy,
                "master_content": master_content,
                "retry_count": 0,
            }

            if final_youtube is not None:
                post_quality_input[
                    "youtube"
                ] = final_youtube

            if final_instagram is not None:
                post_quality_input[
                    "instagram"
                ] = final_instagram

            if final_x is not None:
                post_quality_input[
                    "x"
                ] = final_x

            post_quality_grounding = (
                platform_grounding_workflow
                .invoke(
                    post_quality_input
                )
            )

            post_quality_report = (
                post_quality_grounding[
                    "platform_grounding_report"
                ]
            )

            grounded_youtube = (
                post_quality_grounding.get(
                    "youtube"
                )
            )

            grounded_instagram = (
                post_quality_grounding.get(
                    "instagram"
                )
            )

            grounded_x = (
                post_quality_grounding.get(
                    "x"
                )
            )

            post_grounding_changed = False

            for platform_name, previous, grounded in (
                (
                    "youtube",
                    final_youtube,
                    grounded_youtube,
                ),
                (
                    "instagram",
                    final_instagram,
                    grounded_instagram,
                ),
                (
                    "x",
                    final_x,
                    grounded_x,
                ),
            ):

                if (
                    grounded is not None
                    and (
                        previous is None
                        or grounded.model_dump()
                        != previous.model_dump()
                    )
                ):
                    self.persistence.save_model(
                        run_id,
                        ArtifactType.PLATFORM_CONTENT,
                        grounded,
                        platform=platform_name,
                    )

                    post_grounding_changed = True

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_GROUNDING_REPORT,
                post_quality_report,
            )

            if not post_quality_report.passed:

                status = (
                    RunStatus
                    .FAILED_PLATFORM_GROUNDING
                    .value
                )

                self.persistence.update_status(
                    run_id,
                    status,
                )

                return status

            final_youtube = grounded_youtube
            final_instagram = (
                grounded_instagram
            )
            final_x = grounded_x

            if post_grounding_changed:

                quality_report = (
                    quality_agent.run(
                        strategy=strategy,
                        master_content=(
                            master_content
                        ),
                        youtube=final_youtube,
                        instagram=(
                            final_instagram
                        ),
                        x=final_x,
                    )
                )

                self.persistence.save_model(
                    run_id,
                    ArtifactType.QUALITY_REPORT,
                    quality_report,
                )

                if not quality_report.passed:

                    status = (
                        RunStatus
                        .FAILED_QUALITY_GATE
                        .value
                    )

                    self.persistence.update_status(
                        run_id,
                        status,
                    )

                    return status

        # ==================================================
        # PHASE 8
        # Creative Asset Planning
        # ==================================================

        creative_agent = CreativeAgent(
            llm=self.llm,
        )

        creative_workflow = build_creative_workflow(
            creative_agent=creative_agent,
        )

        creative_input = {
            "strategy": strategy,
            "master_content": master_content,
        }

        # ----------------------------------------------
        # Pass only platforms that actually exist
        # ----------------------------------------------

        if final_youtube is not None:

            creative_input["youtube"] = final_youtube

        if final_instagram is not None:

            creative_input["instagram"] = final_instagram

        if final_x is not None:

            creative_input["x"] = final_x

        # ----------------------------------------------
        # Generate creative briefs/storyboards
        # ----------------------------------------------

        creative_result = creative_workflow.invoke(creative_input)

        creative_assets = creative_result["creative_assets"]

        # ----------------------------------------------
        # Persist creative assets
        # ----------------------------------------------

        self.persistence.save_model(
            run_id,
            ArtifactType.CREATIVE_ASSETS,
            creative_assets,
        )

        # =============================================
        # PHASE 8B
        # Actual Image Generation
        # =============================================

        if self.image_generation_service is not None:

            generated_assets = self.image_generation_service.generate(
                run_id=run_id,
                creative_assets=creative_assets,
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.GENERATED_ASSETS,
                generated_assets,
            )

        # ==================================================
        # Pipeline successfully reaches Human Review
        # ==================================================

        status = RunStatus.READY_FOR_HUMAN_REVIEW.value

        self.persistence.update_status(
            run_id,
            status,
        )

        return status

    def resume_run(
        self,
        run_id: str,
    ) -> str:

        # ==================================================
        # Validate existing run
        # ==================================================

        run = self.persistence.get_run(run_id)

        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        resume_from_failed_platform_grounding = (
            run.status
            == RunStatus.FAILED_PLATFORM_GROUNDING.value
        )

        force_grounding_rebuild = run.status == RunStatus.FAILED_GROUNDING.value

        # ==================================================
        # Load required persisted input
        # ==================================================

        research_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.RESEARCH,
        )

        selected_idea_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.SELECTED_IDEA,
        )

        if research_payload is None:
            raise ValueError(
                "Cannot resume because the " "research artifact is missing."
            )

        if selected_idea_payload is None:
            raise ValueError("Cannot resume because no " "idea has been approved.")

        research = ResearchBrief.model_validate(research_payload)

        selected_idea = ContentIdea.model_validate(selected_idea_payload)

        # ==================================================
        # STEP 1
        # Strategy
        # ==================================================

        strategy_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.STRATEGY,
        )

        strategy_changed = False

        if strategy_payload is not None and not force_grounding_rebuild:

            strategy = ContentStrategy.model_validate(strategy_payload)

        else:

            strategy_agent = StrategyAgent(llm=self.llm)

            strategy = strategy_agent.run(
                research=research,
                selected_idea=selected_idea,
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.STRATEGY,
                strategy,
            )

            strategy_changed = True

        # ==================================================
        # STEP 2
        # Master Content
        # ==================================================

        master_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.MASTER_CONTENT,
        )

        master_agent = MasterContentAgent(llm=self.llm)

        master_changed = False

        if master_payload is not None and not strategy_changed:

            master_content = MasterContent.model_validate(master_payload)

        else:

            master_content = master_agent.run(
                research=research,
                selected_idea=selected_idea,
                strategy=strategy,
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.MASTER_CONTENT,
                master_content,
            )

            master_changed = True

        # ==================================================
        # STEP 3
        # Grounding
        # ==================================================

        grounding_agent = GroundingReviewAgent(llm=self.llm)

        grounding_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.GROUNDING_REPORT,
        )

        grounding_report = None

        if grounding_payload is not None:

            grounding_report = GroundingReport.model_validate(grounding_payload)

        # --------------------------------------------------
        # Re-review when:
        #
        # - no report exists
        # - previous report failed
        # - master content changed
        #
        # This is important because our grounding logic
        # has just been improved.
        # --------------------------------------------------

        if (
            grounding_report is None
            or not grounding_report.passed
            or master_changed
            or grounding_report.review_version
            != GroundingReviewAgent.REVIEW_VERSION
        ):

            grounding_report = grounding_agent.run(
                research=research,
                master_content=master_content,
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.GROUNDING_REPORT,
                grounding_report,
            )

        # ==================================================
        # Grounding Revision
        # ==================================================

        grounding_retry = 0

        if (
            not grounding_report.passed
            and grounding_retry
            < settings.max_grounding_retries
        ):

            remediation = (
                MasterGroundingRemediator()
                .remediate(
                    master_content=(
                        master_content
                    ),
                    grounding_report=(
                        grounding_report
                    ),
                )
            )

            master_content = (
                remediation.master_content
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.MASTER_CONTENT,
                master_content,
            )

            grounding_report = (
                grounding_agent.run(
                    research=research,
                    master_content=master_content,
                )
            )

            self.persistence.save_model(
                run_id,
                ArtifactType.GROUNDING_REPORT,
                grounding_report,
            )

            master_changed = True
            grounding_retry += 1

        # ==================================================
        # Stop if grounding still fails
        # ==================================================

        if not grounding_report.passed:

            status = RunStatus.FAILED_GROUNDING.value

            self.persistence.update_status(
                run_id,
                status,
            )

            return status

        self.persistence.update_status(
            run_id,
            RunStatus.MASTER_CONTENT_READY.value,
        )

        # ==================================================
        # STEP 4
        # Platform Content
        # ==================================================

        youtube_agent = YouTubeAgent(llm=self.llm)

        instagram_agent = InstagramAgent(llm=self.llm)

        x_agent = XAgent(llm=self.llm)

        requested_platforms = set(selected_idea.recommended_platforms)

        youtube = None
        instagram = None
        x_content = None

        missing_platforms = []

        # --------------------------------------------------
        # YouTube
        # --------------------------------------------------

        if "youtube" in requested_platforms:

            youtube_payload = self.persistence.get_latest_payload(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                platform="youtube",
            )

            if youtube_payload is not None and not master_changed:

                youtube = YouTubePackage.model_validate(youtube_payload)

            else:
                missing_platforms.append("youtube")

        # --------------------------------------------------
        # Instagram
        # --------------------------------------------------

        if "instagram" in requested_platforms:

            instagram_payload = self.persistence.get_latest_payload(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                platform="instagram",
            )

            if instagram_payload is not None and not master_changed:

                instagram = InstagramPackage.model_validate(instagram_payload)

            else:
                missing_platforms.append("instagram")

        # --------------------------------------------------
        # X
        # --------------------------------------------------

        if "x" in requested_platforms:

            x_payload = self.persistence.get_latest_payload(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                platform="x",
            )

            if x_payload is not None and not master_changed:

                x_content = XPackage.model_validate(x_payload)

            else:
                missing_platforms.append("x")

        # ==================================================
        # Generate missing/stale platforms only
        # ==================================================

        platform_changed = False

        if missing_platforms:

            platform_workflow = build_platform_content_workflow(
                youtube_agent=youtube_agent,
                instagram_agent=instagram_agent,
                x_agent=x_agent,
            )

            platform_result = platform_workflow.invoke(
                {
                    "strategy": strategy,
                    "master_content": master_content,
                    "platforms": missing_platforms,
                }
            )

            if "youtube" in missing_platforms:

                youtube = platform_result.get("youtube")

                if youtube is not None:

                    self.persistence.save_model(
                        run_id,
                        ArtifactType.PLATFORM_CONTENT,
                        youtube,
                        platform="youtube",
                    )

            if "instagram" in missing_platforms:

                instagram = platform_result.get("instagram")

                if instagram is not None:

                    self.persistence.save_model(
                        run_id,
                        ArtifactType.PLATFORM_CONTENT,
                        instagram,
                        platform="instagram",
                    )

            if "x" in missing_platforms:

                x_content = platform_result.get("x")

                if x_content is not None:

                    self.persistence.save_model(
                        run_id,
                        ArtifactType.PLATFORM_CONTENT,
                        x_content,
                        platform="x",
                    )

            platform_changed = True

        self.persistence.update_status(
            run_id,
            RunStatus.PLATFORM_CONTENT_GENERATED.value,
        )

        # ==================================================
        # PLATFORM GROUNDING
        # ==================================================

        platform_grounding_agent = PlatformGroundingAgent(llm=self.llm)

        platform_grounding_workflow = build_platform_grounding_workflow(
            grounding_agent=(platform_grounding_agent),
            youtube_agent=youtube_agent,
            instagram_agent=instagram_agent,
            x_agent=x_agent,
        )

        platform_grounding_input = {
            # "research": research,
            "strategy": strategy,
            "master_content": master_content,
            "retry_count": 0,
        }

        if youtube is not None:
            platform_grounding_input["youtube"] = youtube

        if instagram is not None:
            platform_grounding_input["instagram"] = instagram

        if x_content is not None:
            platform_grounding_input["x"] = x_content

        # Keep originals so we can detect revisions.

        original_youtube = youtube

        original_instagram = instagram

        original_x = x_content

        platform_grounding_result = platform_grounding_workflow.invoke(
            platform_grounding_input
        )

        platform_grounding_report = platform_grounding_result[
            "platform_grounding_report"
        ]

        youtube = platform_grounding_result.get("youtube")

        instagram = platform_grounding_result.get("instagram")

        x_content = platform_grounding_result.get("x")

        # ==================================================
        # Persist revised platform versions
        # ==================================================

        platform_grounding_changed = False

        if youtube is not None and (
            original_youtube is None
            or youtube.model_dump() != original_youtube.model_dump()
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                youtube,
                platform="youtube",
            )

            platform_grounding_changed = True

        if instagram is not None and (
            original_instagram is None
            or instagram.model_dump() != original_instagram.model_dump()
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                instagram,
                platform="instagram",
            )

            platform_grounding_changed = True

        if x_content is not None and (
            original_x is None or x_content.model_dump() != original_x.model_dump()
        ):

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_CONTENT,
                x_content,
                platform="x",
            )

            platform_grounding_changed = True

        self.persistence.save_model(
            run_id,
            ArtifactType.PLATFORM_GROUNDING_REPORT,
            platform_grounding_report,
        )

        # ==================================================
        # Stop if platform grounding failed
        # ==================================================

        if not platform_grounding_report.passed:

            status = RunStatus.FAILED_PLATFORM_GROUNDING.value

            self.persistence.update_status(
                run_id,
                status,
            )

            return status

        # ==================================================
        # Force downstream regeneration if platform content
        # was corrected.
        # ==================================================

        # ==================================================
        # Downstream invalidation
        #
        # If Platform Grounding changed content during the
        # previous failed execution, old Quality/Creative
        # artifacts are no longer valid.
        #
        # On the next resume the latest platform content may
        # pass without another change, so run status must
        # also force downstream regeneration.
        # ==================================================

        if (
            platform_grounding_changed
            or resume_from_failed_platform_grounding
        ):
            platform_changed = True

        # ==================================================
        # STEP 5
        # Quality
        # ==================================================

        quality_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.QUALITY_REPORT,
        )

        quality_report = None

        if quality_payload is not None:

            quality_report = QualityReport.model_validate(quality_payload)

        quality_ran = False
        quality_content_changed = False

        if (
            quality_report is None
            or not quality_report.passed
            or platform_changed
            or master_changed
        ):

            validator = PlatformValidator()

            quality_agent = QualityReviewAgent(
                llm=self.llm,
                validator=validator,
            )

            quality_workflow = build_quality_workflow(
                quality_agent=quality_agent,
                youtube_agent=youtube_agent,
                instagram_agent=instagram_agent,
                x_agent=x_agent,
            )

            quality_input = {
                "strategy": strategy,
                "master_content": master_content,
                "retry_count": 0,
            }

            if youtube is not None:
                quality_input["youtube"] = youtube

            if instagram is not None:
                quality_input["instagram"] = instagram

            if x_content is not None:
                quality_input["x"] = x_content

            quality_result = quality_workflow.invoke(quality_input)

            quality_report = quality_result["quality_report"]

            final_youtube = quality_result.get("youtube")

            final_instagram = quality_result.get("instagram")

            final_x = quality_result.get("x")

            # ----------------------------------------------
            # Persist revised platform versions
            # ----------------------------------------------

            if final_youtube is not None and (
                youtube is None or final_youtube.model_dump() != youtube.model_dump()
            ):

                self.persistence.save_model(
                    run_id,
                    ArtifactType.PLATFORM_CONTENT,
                    final_youtube,
                    platform="youtube",
                )

                quality_content_changed = True

            if final_instagram is not None and (
                instagram is None
                or final_instagram.model_dump() != instagram.model_dump()
            ):

                self.persistence.save_model(
                    run_id,
                    ArtifactType.PLATFORM_CONTENT,
                    final_instagram,
                    platform="instagram",
                )

                quality_content_changed = True

            if final_x is not None and (
                x_content is None or final_x.model_dump() != x_content.model_dump()
            ):

                self.persistence.save_model(
                    run_id,
                    ArtifactType.PLATFORM_CONTENT,
                    final_x,
                    platform="x",
                )

                quality_content_changed = True

            youtube = final_youtube
            instagram = final_instagram
            x_content = final_x

            self.persistence.save_model(
                run_id,
                ArtifactType.QUALITY_REPORT,
                quality_report,
            )

            quality_ran = True

        # ==================================================
        # Stop if quality still fails
        # ==================================================

        if not quality_report.passed:

            status = RunStatus.FAILED_QUALITY_GATE.value

            self.persistence.update_status(
                run_id,
                status,
            )

            return status

        if quality_content_changed:

            post_quality_input = {
                "strategy": strategy,
                "master_content": master_content,
                "retry_count": 0,
            }

            if youtube is not None:
                post_quality_input[
                    "youtube"
                ] = youtube

            if instagram is not None:
                post_quality_input[
                    "instagram"
                ] = instagram

            if x_content is not None:
                post_quality_input[
                    "x"
                ] = x_content

            post_quality_grounding = (
                platform_grounding_workflow
                .invoke(
                    post_quality_input
                )
            )

            post_quality_report = (
                post_quality_grounding[
                    "platform_grounding_report"
                ]
            )

            grounded_youtube = (
                post_quality_grounding.get(
                    "youtube"
                )
            )
            grounded_instagram = (
                post_quality_grounding.get(
                    "instagram"
                )
            )
            grounded_x = (
                post_quality_grounding.get(
                    "x"
                )
            )

            post_grounding_changed = False

            for platform_name, previous, grounded in (
                (
                    "youtube",
                    youtube,
                    grounded_youtube,
                ),
                (
                    "instagram",
                    instagram,
                    grounded_instagram,
                ),
                (
                    "x",
                    x_content,
                    grounded_x,
                ),
            ):

                if (
                    grounded is not None
                    and (
                        previous is None
                        or grounded.model_dump()
                        != previous.model_dump()
                    )
                ):
                    self.persistence.save_model(
                        run_id,
                        ArtifactType.PLATFORM_CONTENT,
                        grounded,
                        platform=platform_name,
                    )

                    post_grounding_changed = True

            self.persistence.save_model(
                run_id,
                ArtifactType.PLATFORM_GROUNDING_REPORT,
                post_quality_report,
            )

            if not post_quality_report.passed:

                status = (
                    RunStatus
                    .FAILED_PLATFORM_GROUNDING
                    .value
                )

                self.persistence.update_status(
                    run_id,
                    status,
                )

                return status

            youtube = grounded_youtube
            instagram = grounded_instagram
            x_content = grounded_x

            if post_grounding_changed:

                quality_report = (
                    quality_agent.run(
                        strategy=strategy,
                        master_content=(
                            master_content
                        ),
                        youtube=youtube,
                        instagram=instagram,
                        x=x_content,
                    )
                )

                self.persistence.save_model(
                    run_id,
                    ArtifactType.QUALITY_REPORT,
                    quality_report,
                )

                if not quality_report.passed:

                    status = (
                        RunStatus
                        .FAILED_QUALITY_GATE
                        .value
                    )

                    self.persistence.update_status(
                        run_id,
                        status,
                    )

                    return status

        # ==================================================
        # STEP 6
        # Creative Assets
        # ==================================================

        creative_payload = self.persistence.get_latest_payload(
            run_id,
            ArtifactType.CREATIVE_ASSETS,
        )

        creative_assets = None

        creative_changed = False

        if (
            creative_payload is not None
            and not quality_ran
            and not platform_changed
            and not master_changed
        ):

            creative_assets = CreativeAssetBundle.model_validate(creative_payload)

        else:

            creative_agent = CreativeAgent(llm=self.llm)

            creative_workflow = build_creative_workflow(creative_agent=creative_agent)

            creative_input = {
                "strategy": strategy,
                "master_content": master_content,
            }

            if youtube is not None:
                creative_input["youtube"] = youtube

            if instagram is not None:
                creative_input["instagram"] = instagram

            if x_content is not None:
                creative_input["x"] = x_content

            creative_result = creative_workflow.invoke(creative_input)

            creative_assets = creative_result["creative_assets"]

            self.persistence.save_model(
                run_id,
                ArtifactType.CREATIVE_ASSETS,
                creative_assets,
            )

            creative_changed = True

        # ==================================================
        # STEP 7
        # Optional real image generation
        # ==================================================

        if self.image_generation_service is not None:

            generated_payload = self.persistence.get_latest_payload(
                run_id,
                ArtifactType.GENERATED_ASSETS,
            )

            if generated_payload is None or creative_changed:

                generated_assets = self.image_generation_service.generate(
                    run_id=run_id,
                    creative_assets=creative_assets,
                )

                self.persistence.save_model(
                    run_id,
                    ArtifactType.GENERATED_ASSETS,
                    generated_assets,
                )

        # ==================================================
        # READY
        # ==================================================

        status = RunStatus.READY_FOR_HUMAN_REVIEW.value

        self.persistence.update_status(
            run_id,
            status,
        )

        return status

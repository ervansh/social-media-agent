from typing import Literal

from pydantic import BaseModel, Field, create_model

from social_media_agent.config.settings import settings
from social_media_agent.models.content_idea import (
    ContentIdea,
    IdeaBatch,
    Platform,
)
from social_media_agent.models.research import ResearchBrief
from social_media_agent.services.llm.base import LLMProvider


class _BaseIdeaDraft(BaseModel):
    title: str
    hook: str
    angle: str
    target_audience: str
    additional_platforms: list[Platform] = Field(
        default_factory=list
    )
    rationale: str


class _YouTubeIdeaDraft(
    _BaseIdeaDraft
):
    required_platform: Literal[
        "youtube"
    ] = "youtube"


class _InstagramIdeaDraft(
    _BaseIdeaDraft
):
    required_platform: Literal[
        "instagram"
    ] = "instagram"


class _XIdeaDraft(
    _BaseIdeaDraft
):
    required_platform: Literal[
        "x"
    ] = "x"


class _FlexibleIdeaDraft(BaseModel):
    title: str
    hook: str
    angle: str
    target_audience: str
    recommended_platforms: list[
        Platform
    ] = Field(
        min_length=1
    )
    rationale: str


class IdeaAgent:

    REQUIRED_PLATFORM_COUNT = 3

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    def run(
        self,
        research: ResearchBrief,
    ) -> IdeaBatch:

        if (
            settings.idea_count
            < self.REQUIRED_PLATFORM_COUNT
        ):
            raise ValueError(
                "IDEA_COUNT must be at least 3 "
                "to guarantee YouTube, Instagram, "
                "and X idea coverage."
            )

        findings = "\n".join(
            f"- {finding}"
            for finding
            in research.key_findings
        )

        extra_count = (
            settings.idea_count
            - self.REQUIRED_PLATFORM_COUNT
        )

        draft_schema = (
            self._build_draft_schema(
                extra_count
            )
        )

        prompt = f"""
You are a social media content strategist.

Create exactly {settings.idea_count} distinct
content ideas based ONLY on the supplied research.

TOPIC:
{research.topic}

TARGET AUDIENCE:
{research.audience}

RESEARCH SUMMARY:
{research.summary}

KEY FINDINGS:
{findings}

==================================================
PLATFORM COVERAGE
==================================================

The response has three required platform-anchored
ideas plus {extra_count} flexible idea(s).

1. youtube_idea
   - MUST be naturally suitable for YouTube.
   - Prefer depth, explanation, demonstration,
     walkthrough, comparison, or narrative value.

2. instagram_idea
   - MUST be naturally suitable for Instagram.
   - The concept must work well as a visual carousel
     and/or short-form Reel.
   - Prefer concise visual steps, myths vs facts,
     before/after thinking, checklists, frameworks,
     mistakes, or practical swipeable education.

3. x_idea
   - MUST be naturally suitable for X.
   - Prefer concise insight, opinion-neutral
     discussion, practical thread, checklist,
     or conversation-worthy framing.

4. flexible_ideas
   - Generate exactly {extra_count}.
   - Choose whichever platform combination is
     genuinely suitable.

For each anchored idea, required_platform is fixed
by the schema.

additional_platforms may include other platforms
only when the same idea genuinely fits them.

Do not use additional_platforms merely to maximize
coverage.

==================================================
CONTENT RULES
==================================================

- Every idea must be clearly different.
- Keep every idea grounded in the research.
- Do not invent statistics, studies, examples,
  companies, products, or factual claims.
- Focus on practical value for the target audience.
- Avoid generic AI hype.
- Hooks must be concise and compelling.
- Angles must explain the specific perspective.
- Rationale must explain why the idea is relevant.
- Platform values may only be:
  youtube, instagram, x.
- Do not duplicate the same concept across the
  required platform slots.
- The Instagram idea must be genuinely visual,
  not merely a YouTube idea relabeled Instagram.

Return structured JSON only.
"""

        draft = (
            self.llm.generate_structured(
                prompt,
                draft_schema,
                timeout_seconds=(
                    settings
                    .idea_timeout_seconds
                ),
                max_output_tokens=(
                    settings
                    .idea_max_output_tokens
                ),
            )
        )

        ideas = [
            self._anchored_to_content_idea(
                draft.youtube_idea,
                required_platform="youtube",
            ),
            self._anchored_to_content_idea(
                draft.instagram_idea,
                required_platform="instagram",
            ),
            self._anchored_to_content_idea(
                draft.x_idea,
                required_platform="x",
            ),
        ]

        ideas.extend(
            ContentIdea(
                **idea.model_dump()
            )
            for idea
            in draft.flexible_ideas
        )

        if (
            len(ideas)
            != settings.idea_count
        ):
            raise RuntimeError(
                "Idea generation returned an "
                "unexpected idea count."
            )

        self._validate_platform_coverage(
            ideas
        )

        return IdeaBatch(
            ideas=ideas
        )

    @staticmethod
    def _build_draft_schema(
        extra_count: int,
    ):

        if extra_count == 0:

            flexible_field = (
                list[_FlexibleIdeaDraft],
                Field(
                    default_factory=list,
                    min_length=0,
                    max_length=0,
                ),
            )

        else:

            flexible_field = (
                list[_FlexibleIdeaDraft],
                Field(
                    min_length=extra_count,
                    max_length=extra_count,
                ),
            )

        return create_model(
            "IdeaCoverageDraft",
            youtube_idea=(
                _YouTubeIdeaDraft,
                ...,
            ),
            instagram_idea=(
                _InstagramIdeaDraft,
                ...,
            ),
            x_idea=(
                _XIdeaDraft,
                ...,
            ),
            flexible_ideas=(
                flexible_field
            ),
        )

    @staticmethod
    def _anchored_to_content_idea(
        draft: _BaseIdeaDraft,
        *,
        required_platform: Platform,
    ) -> ContentIdea:

        platforms = [
            required_platform
        ]

        for platform in (
            draft.additional_platforms
        ):
            if platform not in platforms:
                platforms.append(
                    platform
                )

        return ContentIdea(
            title=draft.title,
            hook=draft.hook,
            angle=draft.angle,
            target_audience=(
                draft.target_audience
            ),
            recommended_platforms=(
                platforms
            ),
            rationale=draft.rationale,
        )

    @staticmethod
    def _validate_platform_coverage(
        ideas: list[ContentIdea],
    ) -> None:

        covered = {
            platform
            for idea in ideas
            for platform
            in idea.recommended_platforms
        }

        missing = {
            "youtube",
            "instagram",
            "x",
        } - covered

        if missing:
            raise RuntimeError(
                "Idea platform coverage invariant "
                "failed. Missing: "
                + ", ".join(
                    sorted(missing)
                )
            )

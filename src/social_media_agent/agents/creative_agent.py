from pydantic import BaseModel

from social_media_agent.config.settings import settings
from social_media_agent.models.content_strategy import (
    ContentStrategy,
)
from social_media_agent.models.creative_assets import (
    CreativeAssetBundle,
    ImageBrief,
    StoryboardScene,
    VideoStoryboard,
)
from social_media_agent.models.master_content import (
    MasterContent,
)
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.services.llm.base import (
    LLMProvider,
)


# ==========================================================
# Internal LLM response models
#
# IMPORTANT:
# The LLM does NOT decide platform, asset_type or dimensions.
# Those values are deterministic and assigned by Python.
# ==========================================================


class _ImageBriefDraft(BaseModel):
    objective: str
    visual_concept: str
    text_overlay: str | None = None
    image_prompt: str
    negative_prompt: str | None = None


class _StoryboardDraft(BaseModel):
    scenes: list[StoryboardScene]


class CreativeAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    # ======================================================
    # Image Brief
    # ======================================================

    def _generate_image_brief(
        self,
        *,
        platform: str,
        asset_type: str,
        width: int,
        height: int,
        source_context: str,
        tone: str,
    ) -> ImageBrief:

        prompt = f"""
You are a creative director for social media.

Create ONE visual image brief.

PLATFORM:
{platform}

ASSET TYPE:
{asset_type}

TONE:
{tone}

SOURCE CONTENT:

{source_context}

RULES:

- Create exactly one image concept.
- Do not create a storyboard.
- Do not add new factual claims.
- Do not invent statistics, product capabilities,
  people, companies, studies, or examples.
- Visualize only information contained in SOURCE CONTENT.
- Keep text overlay short.
- Keep image_prompt visually specific but concise.
- Keep negative_prompt concise.
- Do not explain your reasoning.
- Do not include platform dimensions.
- Do not include platform or asset_type in the response.

Return structured JSON only.
"""

        draft = self.llm.generate_structured(
            prompt,
            _ImageBriefDraft,
            timeout_seconds=(
                settings.creative_timeout_seconds
            ),
            max_output_tokens=(
                settings.creative_max_output_tokens
            ),
        )

        return ImageBrief(
            platform=platform,
            asset_type=asset_type,
            width=width,
            height=height,
            objective=draft.objective,
            visual_concept=draft.visual_concept,
            text_overlay=draft.text_overlay,
            image_prompt=draft.image_prompt,
            negative_prompt=draft.negative_prompt,
        )

    # ======================================================
    # Video Storyboard
    # ======================================================

    def _generate_storyboard(
        self,
        *,
        platform: str,
        asset_type: str,
        source_context: str,
        tone: str,
    ) -> VideoStoryboard:

        prompt = f"""
You are a creative director creating a short-form
social media video storyboard.

PLATFORM:
{platform}

ASSET TYPE:
{asset_type}

TONE:
{tone}

SOURCE CONTENT:

{source_context}

Create exactly
{settings.instagram_reel_scene_count}
concise storyboard scenes.

RULES:

- Use only SOURCE CONTENT.
- Do not introduce new factual claims.
- Do not invent statistics or product capabilities.
- Keep narration concise.
- Keep visual_direction concise.
- Keep on_screen_text short.
- Each scene must have a unique scene_number.
- Do not generate image briefs.
- Do not include platform or asset_type in the response.
- Do not explain your reasoning.

Return structured JSON only.
"""

        draft = self.llm.generate_structured(
            prompt,
            _StoryboardDraft,
            timeout_seconds=(
                settings.creative_timeout_seconds
            ),
            max_output_tokens=(
                settings.creative_max_output_tokens
            ),
        )

        # Deterministic upper bound.
        scenes = draft.scenes[
            : settings.instagram_reel_scene_count
        ]

        return VideoStoryboard(
            platform=platform,
            asset_type=asset_type,
            scenes=scenes,
        )

    # ======================================================
    # Main orchestration
    # ======================================================

    def run(
        self,
        strategy: ContentStrategy,
        master_content: MasterContent,
        youtube: YouTubePackage | None = None,
        instagram: InstagramPackage | None = None,
        x: XPackage | None = None,
    ) -> CreativeAssetBundle:

        images: list[ImageBrief] = []
        storyboards: list[VideoStoryboard] = []

        # ==================================================
        # YouTube
        #
        # Only thumbnail image.
        # No YouTube storyboard is generated here.
        # ==================================================

        if youtube is not None:

            youtube_context = f"""
TITLE:
{youtube.title}

THUMBNAIL CONCEPT:
{youtube.thumbnail_concept}

CORE MESSAGE:
{master_content.core_message}
"""

            images.append(
                self._generate_image_brief(
                    platform="youtube",
                    asset_type="thumbnail",
                    width=(
                        settings
                        .youtube_thumbnail_width
                    ),
                    height=(
                        settings
                        .youtube_thumbnail_height
                    ),
                    source_context=youtube_context,
                    tone=strategy.tone,
                )
            )

        # ==================================================
        # Instagram Carousel
        #
        # One small structured call PER SLIDE.
        # This prevents giant JSON responses.
        # ==================================================

        if instagram is not None:

            for slide in instagram.carousel_slides:

                slide_context = f"""
CAROUSEL SLIDE:
{slide.position}

HEADLINE:
{slide.headline}

BODY:
{slide.body}

CORE MESSAGE:
{master_content.core_message}
"""

                images.append(
                    self._generate_image_brief(
                        platform="instagram",
                        asset_type=(
                            "carousel_slide_"
                            f"{slide.position}"
                        ),
                        width=(
                            settings
                            .instagram_asset_width
                        ),
                        height=(
                            settings
                            .instagram_asset_height
                        ),
                        source_context=slide_context,
                        tone=strategy.tone,
                    )
                )

            # ==============================================
            # Instagram Reel
            #
            # Separate storyboard call.
            # ==============================================

            reel_context = f"""
REEL HOOK:
{instagram.reel_hook}

REEL SCRIPT:
{instagram.reel_script}

CORE MESSAGE:
{master_content.core_message}
"""

            storyboards.append(
                self._generate_storyboard(
                    platform="instagram",
                    asset_type="reel_storyboard",
                    source_context=reel_context,
                    tone=strategy.tone,
                )
            )

        # ==================================================
        # X Supporting Visual
        # ==================================================

        if x is not None:

            x_context = f"""
X POST:
{x.single_post}

CALL TO ACTION:
{x.call_to_action}

CORE MESSAGE:
{master_content.core_message}
"""

            images.append(
                self._generate_image_brief(
                    platform="x",
                    asset_type="supporting_visual",
                    width=settings.x_asset_width,
                    height=settings.x_asset_height,
                    source_context=x_context,
                    tone=strategy.tone,
                )
            )

        # ==================================================
        # Assemble bundle deterministically
        # ==================================================

        return CreativeAssetBundle(
            images=images,
            storyboards=storyboards,
        )
from pydantic import (
    BaseModel,
    Field,
)

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
# The LLM does NOT decide platform, asset_type, dimensions,
# or storyboard scene numbers. Python owns those values.
#
# All free-text fields are bounded in the JSON schema so
# structured generation cannot expand until num_predict
# truncates the response mid-JSON.
# ==========================================================


class _ImageBriefDraft(BaseModel):
    objective: str = Field(
        min_length=1,
        max_length=180,
    )

    visual_concept: str = Field(
        min_length=1,
        max_length=360,
    )

    text_overlay: str | None = Field(
        default=None,
        max_length=80,
    )

    image_prompt: str = Field(
        min_length=1,
        max_length=900,
    )

    negative_prompt: str | None = Field(
        default=None,
        max_length=300,
    )


class _StoryboardSceneDraft(BaseModel):
    narration: str = Field(
        min_length=1,
        max_length=220,
    )

    visual_direction: str = Field(
        min_length=1,
        max_length=320,
    )

    on_screen_text: str | None = Field(
        default=None,
        max_length=100,
    )


class _StoryboardDraft(BaseModel):
    scenes: list[
        _StoryboardSceneDraft
    ] = Field(
        min_length=settings.instagram_reel_scene_count,
        max_length=settings.instagram_reel_scene_count,
    )


class CreativeAgent:

    def __init__(
        self,
        llm: LLMProvider,
    ):
        self.llm = llm

    # ======================================================
    # Shared helpers
    # ======================================================

    @staticmethod
    def _bounded_context(
        source_context: str,
    ) -> str:

        normalized = " ".join(
            source_context.split()
        )

        limit = (
            settings
            .creative_source_context_max_chars
        )

        if len(normalized) <= limit:
            return normalized

        truncated = normalized[
            :limit
        ]

        if " " in truncated:
            truncated = truncated.rsplit(
                " ",
                1,
            )[0]

        return (
            truncated.rstrip()
            + "..."
        )

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

        bounded_context = (
            self._bounded_context(
                source_context
            )
        )

        prompt = f"""
You are a creative director for social media.

Create exactly ONE concise visual image brief.

PLATFORM:
{platform}

ASSET TYPE:
{asset_type}

TONE:
{tone}

SOURCE CONTENT:
{bounded_context}

STRICT OUTPUT LIMITS:

- objective: maximum 180 characters.
- visual_concept: maximum 360 characters.
- text_overlay: maximum 80 characters.
- image_prompt: maximum 900 characters.
- negative_prompt: maximum 300 characters.

CONTENT RULES:

- Create exactly one image concept.
- Do not create a storyboard.
- Do not add new factual claims.
- Do not invent statistics, product capabilities,
  people, companies, studies, or examples.
- Visualize only information contained in SOURCE CONTENT.
- Keep text overlay short.
- Describe composition, subject, setting, lighting,
  visual hierarchy, and style concisely.
- Do not write explanations, disclaimers, conclusions,
  marketing copy, or paragraphs of analysis.
- Do not repeat SOURCE CONTENT.
- Do not include platform dimensions.
- Do not include platform or asset_type in the response.
- Fill only the JSON schema fields.

Return structured JSON only.
"""

        draft = self.llm.generate_structured(
            prompt,
            _ImageBriefDraft,
            timeout_seconds=(
                settings.creative_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .creative_image_brief_max_output_tokens
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

        bounded_context = (
            self._bounded_context(
                source_context
            )
        )

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
{bounded_context}

Create exactly
{settings.instagram_reel_scene_count}
concise storyboard scenes.

STRICT OUTPUT LIMITS PER SCENE:

- narration: maximum 220 characters.
- visual_direction: maximum 320 characters.
- on_screen_text: maximum 100 characters.

CONTENT RULES:

- Use only SOURCE CONTENT.
- Do not introduce new factual claims.
- Do not invent statistics or product capabilities.
- Keep every scene concise and visually distinct.
- Do not include scene numbers in generated content;
  Python assigns them deterministically.
- Do not generate image briefs.
- Do not include platform or asset_type in the response.
- Do not explain your reasoning.
- Fill only the JSON schema fields.

Return structured JSON only.
"""

        draft = self.llm.generate_structured(
            prompt,
            _StoryboardDraft,
            timeout_seconds=(
                settings.creative_timeout_seconds
            ),
            max_output_tokens=(
                settings
                .creative_storyboard_max_output_tokens
            ),
        )

        scenes = [
            StoryboardScene(
                scene_number=index,
                narration=scene.narration,
                visual_direction=(
                    scene.visual_direction
                ),
                on_screen_text=(
                    scene.on_screen_text
                ),
            )
            for index, scene
            in enumerate(
                draft.scenes,
                start=1,
            )
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
        # One bounded structured call per slide.
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

        return CreativeAssetBundle(
            images=images,
            storyboards=storyboards,
        )

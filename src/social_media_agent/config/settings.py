from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "social-media-agent"
    app_env: str = "development"
    log_level: str = "INFO"

    llm_provider: str = "ollama"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_timeout_seconds: int = 180
    ollama_think: bool = False

    llm_temperature: float = 0.0

    search_provider: str = "ddgs"
    search_region: str = "us-en"
    research_query_count: int = 2
    search_results_per_query: int = 3
    idea_count: int = 5
    research_snippet_max_chars: int = 1200

    youtube_title_max_chars: int = 100
    youtube_description_max_chars: int = 5000
    youtube_script_target_words: int = 600

    instagram_carousel_slide_count: int = 7

    x_post_max_chars: int = 280
    x_thread_post_count: int = 5

    max_quality_retries: int = 1

    long_generation_timeout_seconds: int = 300
    long_generation_max_output_tokens: int = 1600

    max_grounding_retries: int = 1

    youtube_thumbnail_width: int = 3840
    youtube_thumbnail_height: int = 2160

    instagram_asset_width: int = 1080
    instagram_asset_height: int = 1350

    instagram_reel_width: int = 1080
    instagram_reel_height: int = 1920

    database_url: str = (
    "sqlite:///./data/database/social_media_agent.db"
    )
    database_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    image_generation_enabled: bool = False
    image_provider: str = "disabled"

    generated_assets_dir: str = (
        "data/output/generated_assets"
    )

    image_generation_timeout_seconds: int = 300
    image_size_multiple: int = 16

    openai_api_key: str | None = None
    openai_image_base_url: str = (
        "https://api.openai.com/v1"
    )

    openai_image_model: str = (
        "gpt-image-2.5-flare"
    )

    openai_image_quality: str = "medium"
    openai_image_output_format: str = "png"

    publishing_mode: str = "dry_run"
    x_api_base_url: str = "https://api.x.com/2"
    x_user_access_token: str | None = None
    x_request_timeout_seconds: int = 60

    grounding_timeout_seconds: int = 300
    grounding_max_output_tokens: int = 1400
    grounding_source_max_chars: int = 800
    grounding_max_sources: int = 6

    idea_timeout_seconds: int = 300
    idea_max_output_tokens: int = 1400

    master_content_timeout_seconds: int = 300
    master_content_max_output_tokens: int = 1400
    quality_timeout_seconds: int = 300
    quality_max_output_tokens: int = 900
    creative_timeout_seconds: int = 300
    creative_max_output_tokens: int = 1200

    instagram_reel_scene_count: int = 5
    
    x_asset_width: int = 1600
    x_asset_height: int = 900

    platform_grounding_timeout_seconds: int = 300
    platform_grounding_max_output_tokens: int = 800
    max_platform_grounding_retries: int = 1


settings = Settings()

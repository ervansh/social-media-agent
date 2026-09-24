from social_media_agent.config.settings import settings


def test_application_name():
    assert settings.app_name == "social-media-agent"


def test_llm_provider():
    assert settings.llm_provider in {
        "ollama",
        "openai",
    }
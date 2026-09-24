from social_media_agent.agents.x_agent import XAgent


def test_x_text_is_trimmed_to_limit():

    text = (
        "This is a very long X post. "
        * 50
    )

    result = XAgent._fit_to_limit(
        text,
        280,
    )

    assert len(result) <= 280

def test_x_text_under_limit_is_unchanged():

    text = "Short valid X post."

    result = XAgent._fit_to_limit(
        text,
        280,
    )

    assert result == text

def test_x_package_uses_single_post():

    from social_media_agent.models.platform_content import (
        XPackage,
    )

    package = XPackage(
        single_post="Short X post.",
        thread=[
            "Thread post 1.",
            "Thread post 2.",
        ],
        call_to_action="Learn more.",
    )

    assert package.single_post == "Short X post."
    assert len(package.thread) == 2
    assert package.call_to_action == "Learn more."
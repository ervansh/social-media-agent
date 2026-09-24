from social_media_agent.config.settings import settings
from social_media_agent.models.platform_content import (
    InstagramPackage,
    XPackage,
    YouTubePackage,
)
from social_media_agent.models.quality import (
    QualityIssue,
)


class PlatformValidator:

    def validate(
        self,
        youtube: YouTubePackage | None = None,
        instagram: InstagramPackage | None = None,
        x: XPackage | None = None,
    ) -> list[QualityIssue]:

        issues: list[QualityIssue] = []

        if youtube:

            if (
                len(youtube.title)
                > settings.youtube_title_max_chars
            ):
                issues.append(
                    QualityIssue(
                        platform="youtube",
                        severity="error",
                        field="title",
                        message=(
                            "YouTube title exceeds "
                            "configured limit."
                        ),
                    )
                )

            if (
                len(youtube.description)
                > settings.youtube_description_max_chars
            ):
                issues.append(
                    QualityIssue(
                        platform="youtube",
                        severity="error",
                        field="description",
                        message=(
                            "YouTube description exceeds "
                            "configured limit."
                        ),
                    )
                )

        if x:

            if len(x.single_post) > settings.x_post_max_chars:
                issues.append(
                    QualityIssue(
                        platform="x",
                        severity="error",
                        field="single_post",
                        message="X post exceeds configured character limit.",
                    )
                )

            for index, post in enumerate(
                x.thread,
                start=1,
            ):
                if len(post) > settings.x_post_max_chars:
                    issues.append(
                        QualityIssue(
                            platform="x",
                            severity="error",
                            field=f"thread[{index}]",
                            message=(
                                "X thread post exceeds "
                                "configured character limit."
                            ),
                        )
                    )

        if instagram:

            if not instagram.carousel_slides:
                issues.append(
                    QualityIssue(
                        platform="instagram",
                        severity="error",
                        field="carousel_slides",
                        message="Instagram carousel contains no slides.",
                    )
                )

        return issues
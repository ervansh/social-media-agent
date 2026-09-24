from dataclasses import dataclass

from social_media_agent.models.grounding import (
    GroundingReport,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)


@dataclass(frozen=True)
class MasterGroundingRemediationResult:
    master_content: MasterContent
    grounding_report: GroundingReport


class MasterGroundingRemediator:

    TITLE_FALLBACKS = (
        "AI Testing Review",
        "AI Testing Overview",
        "AI Testing Notes",
    )

    HOOK_FALLBACKS = (
        "Review the points below.",
        "Consider the points below.",
        "Use the points below as a review guide.",
    )

    CORE_MESSAGE_FALLBACKS = (
        "Use the source-supported points below.",
        "Focus on the retained source-supported points.",
        "Keep the discussion limited to the retained points.",
    )

    SECTION_HEADING_FALLBACKS = (
        "Key Points",
        "Review Points",
        "Source-Supported Points",
    )

    SECTION_PURPOSE_FALLBACKS = (
        "Organize the retained points.",
        "Present the retained points clearly.",
        "Summarize the retained points.",
    )

    RECOMMENDATION_FALLBACKS = (
        "Review the retained points.",
        "Use the retained points for evaluation.",
        "Compare the retained points with your requirements.",
    )

    TAKEAWAY_FALLBACKS = (
        "Review the retained source-supported points.",
        "Keep conclusions limited to the retained points.",
        "Use the retained points as the basis for evaluation.",
    )

    CTA_FALLBACKS = (
        "Review the points above.",
        "Compare the points above with your requirements.",
        "Use the points above for your evaluation.",
    )

    def remediate(
        self,
        *,
        master_content: MasterContent,
        grounding_report: GroundingReport,
    ) -> MasterGroundingRemediationResult:

        error_claims = {
            self._normalize(
                issue.claim
            )
            for issue
            in grounding_report.issues
            if issue.severity == "error"
        }

        if not error_claims:
            return MasterGroundingRemediationResult(
                master_content=master_content,
                grounding_report=grounding_report,
            )

        title = self._replace_if_error(
            master_content.title,
            error_claims,
            self.TITLE_FALLBACKS,
        )

        hook = self._replace_if_error(
            master_content.hook,
            error_claims,
            self.HOOK_FALLBACKS,
        )

        core_message = self._replace_if_error(
            master_content.core_message,
            error_claims,
            self.CORE_MESSAGE_FALLBACKS,
        )

        sections = []

        for section in master_content.sections:

            heading = self._replace_if_error(
                section.heading,
                error_claims,
                self.SECTION_HEADING_FALLBACKS,
            )

            purpose = self._replace_if_error(
                section.purpose,
                error_claims,
                self.SECTION_PURPOSE_FALLBACKS,
            )

            key_points = [
                point
                for point
                in section.key_points
                if self._normalize(
                    point
                )
                not in error_claims
            ]

            if not key_points:
                continue

            sections.append(
                MasterSection(
                    heading=heading,
                    purpose=purpose,
                    key_points=key_points,
                )
            )

        if not sections:

            section_heading = (
                self._choose_replacement(
                    error_claims,
                    self.SECTION_HEADING_FALLBACKS,
                )
            )

            section_purpose = (
                self._choose_replacement(
                    error_claims,
                    self.SECTION_PURPOSE_FALLBACKS,
                )
            )

            recommendation = (
                self._choose_replacement(
                    error_claims,
                    self.RECOMMENDATION_FALLBACKS,
                )
            )

            sections = [
                MasterSection(
                    heading=section_heading,
                    purpose=section_purpose,
                    key_points=[
                        recommendation
                    ],
                )
            ]

        key_takeaways = [
            takeaway
            for takeaway
            in master_content.key_takeaways
            if self._normalize(
                takeaway
            )
            not in error_claims
        ]

        if not key_takeaways:
            key_takeaways = [
                self._choose_replacement(
                    error_claims,
                    self.TAKEAWAY_FALLBACKS,
                )
            ]

        call_to_action = (
            self._replace_if_error(
                master_content.call_to_action,
                error_claims,
                self.CTA_FALLBACKS,
            )
        )

        remediated = MasterContent(
            title=title,
            hook=hook,
            core_message=core_message,
            sections=sections,
            key_takeaways=key_takeaways,
            call_to_action=call_to_action,
            sources=master_content.sources,
        )

        self._assert_errors_removed(
            remediated,
            error_claims,
        )

        remaining_claims = (
            self._content_values(
                remediated
            )
        )

        remaining_warnings = [
            issue
            for issue
            in grounding_report.issues
            if (
                issue.severity == "warning"
                and self._normalize(
                    issue.claim
                )
                in remaining_claims
            )
        ]

        report = GroundingReport(
            review_version=(
                grounding_report.review_version
            ),
            passed=False,
            summary=(
                "Deterministic remediation was "
                "applied. The corrected Master "
                "Content requires a fresh grounding "
                "review before it can pass."
            ),
            issues=remaining_warnings,
        )

        return MasterGroundingRemediationResult(
            master_content=remediated,
            grounding_report=report,
        )

    @classmethod
    def _replace_if_error(
        cls,
        value: str,
        error_claims: set[str],
        replacements: tuple[str, ...],
    ) -> str:

        if (
            cls._normalize(value)
            not in error_claims
        ):
            return value

        return cls._choose_replacement(
            error_claims,
            replacements,
        )

    @classmethod
    def _choose_replacement(
        cls,
        error_claims: set[str],
        replacements: tuple[str, ...],
    ) -> str:

        for replacement in replacements:

            if (
                cls._normalize(
                    replacement
                )
                not in error_claims
            ):
                return replacement

        raise RuntimeError(
            "Grounding remediation exhausted "
            "all neutral fallback candidates."
        )

    @classmethod
    def _assert_errors_removed(
        cls,
        master_content: MasterContent,
        error_claims: set[str],
    ) -> None:

        remaining = (
            cls._content_values(
                master_content
            )
        )

        unresolved = (
            error_claims
            & remaining
        )

        if unresolved:
            raise RuntimeError(
                "Grounding remediation left "
                "unsupported claims in Master "
                "Content: "
                + " | ".join(
                    sorted(unresolved)
                )
            )

    @classmethod
    def _content_values(
        cls,
        master_content: MasterContent,
    ) -> set[str]:

        values = {
            cls._normalize(
                master_content.title
            ),
            cls._normalize(
                master_content.hook
            ),
            cls._normalize(
                master_content.core_message
            ),
            cls._normalize(
                master_content.call_to_action
            ),
        }

        for section in master_content.sections:

            values.add(
                cls._normalize(
                    section.heading
                )
            )

            values.add(
                cls._normalize(
                    section.purpose
                )
            )

            values.update(
                cls._normalize(
                    point
                )
                for point
                in section.key_points
            )

        values.update(
            cls._normalize(
                takeaway
            )
            for takeaway
            in master_content.key_takeaways
        )

        return values

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        return " ".join(
            value.split()
        ).strip().casefold()

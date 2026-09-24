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

    SAFE_TITLE = (
        "Evidence-Based AI Testing Review"
    )

    SAFE_HOOK = (
        "Separate demonstrated AI testing "
        "capabilities from assumptions before "
        "relying on them in your workflow."
    )

    SAFE_CORE_MESSAGE = (
        "Use the available evidence to distinguish "
        "demonstrated AI testing capabilities from "
        "claims that still need verification."
    )

    SAFE_SECTION_HEADING = (
        "Practical Evaluation"
    )

    SAFE_SECTION_PURPOSE = (
        "Keep the discussion useful without "
        "exceeding the supplied evidence."
    )

    SAFE_RECOMMENDATION = (
        "When evaluating an AI testing capability, "
        "compare its documented behavior with your "
        "own QA requirements before relying on it."
    )

    SAFE_TAKEAWAY = (
        "Treat unsupported benefits or limitations "
        "as questions to verify, not established facts."
    )

    SAFE_CALL_TO_ACTION = (
        "Review the documented capability against "
        "your own testing requirements."
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
            self.SAFE_TITLE,
        )

        hook = self._replace_if_error(
            master_content.hook,
            error_claims,
            self.SAFE_HOOK,
        )

        core_message = self._replace_if_error(
            master_content.core_message,
            error_claims,
            self.SAFE_CORE_MESSAGE,
        )

        sections = []

        for section in master_content.sections:

            heading = self._replace_if_error(
                section.heading,
                error_claims,
                self.SAFE_SECTION_HEADING,
            )

            purpose = self._replace_if_error(
                section.purpose,
                error_claims,
                self.SAFE_SECTION_PURPOSE,
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
            sections = [
                MasterSection(
                    heading=(
                        self.SAFE_SECTION_HEADING
                    ),
                    purpose=(
                        self.SAFE_SECTION_PURPOSE
                    ),
                    key_points=[
                        self.SAFE_RECOMMENDATION
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
                self.SAFE_TAKEAWAY
            ]

        call_to_action = (
            self._replace_if_error(
                master_content.call_to_action,
                error_claims,
                self.SAFE_CALL_TO_ACTION,
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
            passed=True,
            summary=(
                "Unsupported factual claims were "
                "removed deterministically. "
                "Remaining warnings are non-blocking."
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
        replacement: str,
    ) -> str:

        if (
            cls._normalize(value)
            in error_claims
        ):
            return replacement

        return value

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

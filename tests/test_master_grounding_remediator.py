from social_media_agent.models.grounding import (
    GroundingIssue,
    GroundingReport,
)
from social_media_agent.models.master_content import (
    MasterContent,
    MasterSection,
)
from social_media_agent.services.grounding.master_grounding_remediator import (
    MasterGroundingRemediator,
)


def build_master():

    return MasterContent(
        title="Self-Healing Test Claims",
        hook=(
            "Self-healing is not universally "
            "applicable."
        ),
        core_message=(
            "Some tools demonstrate "
            "self-healing capabilities."
        ),
        sections=[
            MasterSection(
                heading="Capabilities",
                purpose=(
                    "Review documented capabilities."
                ),
                key_points=[
                    (
                        "Some tools demonstrate "
                        "self-healing capabilities."
                    ),
                    (
                        "Self-healing may miss "
                        "unexpected changes."
                    ),
                ],
            ),
            MasterSection(
                heading="Efficiency",
                purpose=(
                    "Discuss efficiency outcomes."
                ),
                key_points=[
                    (
                        "AI significantly boosts "
                        "QA efficiency."
                    )
                ],
            ),
        ],
        key_takeaways=[
            (
                "Verify documented behavior "
                "in your own workflow."
            ),
            (
                "AI always improves reliability."
            ),
        ],
        call_to_action=(
            "Review the documented capability."
        ),
        sources=[],
    )


def build_report():

    return GroundingReport(
        passed=False,
        summary=(
            "Some claims exceed evidence."
        ),
        issues=[
            GroundingIssue(
                severity="error",
                claim=(
                    "Self-healing is not "
                    "universally applicable."
                ),
                reason="Unsupported limitation.",
            ),
            GroundingIssue(
                severity="error",
                claim=(
                    "Self-healing may miss "
                    "unexpected changes."
                ),
                reason="Unsupported consequence.",
            ),
            GroundingIssue(
                severity="error",
                claim=(
                    "AI significantly boosts "
                    "QA efficiency."
                ),
                reason="Unsupported outcome.",
            ),
            GroundingIssue(
                severity="error",
                claim=(
                    "AI always improves reliability."
                ),
                reason="Unsupported outcome.",
            ),
            GroundingIssue(
                severity="warning",
                claim=(
                    "Some tools demonstrate "
                    "self-healing capabilities."
                ),
                reason=(
                    "Keep scope limited "
                    "to demonstrated tools."
                ),
            ),
        ],
    )


def test_remediator_removes_all_error_claims():

    result = (
        MasterGroundingRemediator()
        .remediate(
            master_content=build_master(),
            grounding_report=build_report(),
        )
    )

    payload = (
        result.master_content
        .model_dump_json()
        .casefold()
    )

    assert (
        "not universally applicable"
        not in payload
    )

    assert (
        "may miss unexpected changes"
        not in payload
    )

    assert (
        "significantly boosts"
        not in payload
    )

    assert (
        "always improves reliability"
        not in payload
    )

    assert (
        result.grounding_report.passed
        is True
    )


def test_remediator_preserves_supported_or_warning_content():

    result = (
        MasterGroundingRemediator()
        .remediate(
            master_content=build_master(),
            grounding_report=build_report(),
        )
    )

    payload = (
        result.master_content
        .model_dump_json()
    )

    assert (
        "Some tools demonstrate "
        "self-healing capabilities."
        in payload
    )

    assert (
        len(
            result.grounding_report
            .issues
        )
        == 1
    )

    assert (
        result.grounding_report
        .issues[0]
        .severity
        == "warning"
    )


def test_remediator_keeps_master_structurally_valid():

    master = MasterContent(
        title="Unsupported title",
        hook="Unsupported hook",
        core_message="Unsupported core",
        sections=[
            MasterSection(
                heading="Unsupported heading",
                purpose="Unsupported purpose",
                key_points=[
                    "Unsupported key point"
                ],
            )
        ],
        key_takeaways=[
            "Unsupported takeaway"
        ],
        call_to_action="Unsupported CTA",
        sources=[],
    )

    error_values = [
        master.title,
        master.hook,
        master.core_message,
        master.sections[0].heading,
        master.sections[0].purpose,
        master.sections[0].key_points[0],
        master.key_takeaways[0],
        master.call_to_action,
    ]

    report = GroundingReport(
        passed=False,
        summary="Everything failed.",
        issues=[
            GroundingIssue(
                severity="error",
                claim=value,
                reason="Unsupported.",
            )
            for value in error_values
        ],
    )

    result = (
        MasterGroundingRemediator()
        .remediate(
            master_content=master,
            grounding_report=report,
        )
    )

    remediated = (
        result.master_content
    )

    assert remediated.title
    assert remediated.hook
    assert remediated.core_message
    assert remediated.sections
    assert (
        remediated.sections[0]
        .key_points
    )
    assert remediated.key_takeaways
    assert remediated.call_to_action

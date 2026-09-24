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
        is False
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


def test_remediator_replaces_previous_fallbacks_when_they_become_errors():

    master = MasterContent(
        title=(
            "Evidence-Based AI Testing Review"
        ),
        hook=(
            "Separate demonstrated AI testing "
            "capabilities from assumptions before "
            "relying on them in your workflow."
        ),
        core_message=(
            "Use the available evidence to distinguish "
            "demonstrated AI testing capabilities from "
            "claims that still need verification."
        ),
        sections=[
            MasterSection(
                heading="A Balanced View",
                purpose="Present retained points.",
                key_points=[
                    (
                        "Some tools demonstrate "
                        "self-healing capabilities."
                    )
                ],
            )
        ],
        key_takeaways=[
            (
                "Review retained points carefully."
            )
        ],
        call_to_action=(
            "Review the documented capability against "
            "your own testing requirements."
        ),
        sources=[],
    )

    error_values = [
        master.title,
        master.hook,
        master.core_message,
        master.call_to_action,
    ]

    report = GroundingReport(
        review_version=2,
        passed=False,
        summary=(
            "Previous fallback wording was "
            "classified as unsupported."
        ),
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

    remediated = result.master_content

    assert (
        remediated.title
        == "AI Testing Review"
    )

    assert (
        remediated.hook
        == "Review the points below."
    )

    assert (
        remediated.core_message
        == "Use the source-supported points below."
    )

    assert (
        remediated.call_to_action
        == "Review the points above."
    )

    payload = (
        remediated
        .model_dump_json()
        .casefold()
    )

    for error_value in error_values:
        assert (
            error_value.casefold()
            not in payload
        )

    assert (
        result.grounding_report.passed
        is False
    )

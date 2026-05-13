"""Smoke tests for diagnosis aggregation."""

from app.core.models.issue import Issue
from app.core.skills.metadata_quality_diagnosis import (
    MetadataQualityDiagnosisInput,
    MetadataQualityDiagnosisSkill,
)
from app.main import health_check


def test_quality_diagnosis_aggregates_upstream_issues() -> None:
    skill = MetadataQualityDiagnosisSkill()
    upstream_issues = [
        Issue(
            issue_id="issue-1",
            object_type="table",
            object_name="sales_order",
            issue_type="missing_table_description",
            severity="medium",
            evidence=["table description is blank"],
        ),
        Issue(
            issue_id="issue-2",
            object_type="field",
            object_name="sales_order.order__id",
            issue_type="naming_contains_repeated_underscore",
            severity="low",
            evidence=["field name contains repeated underscore"],
        ),
    ]

    result = skill.run(
        MetadataQualityDiagnosisInput(tables=[], upstream_issues=upstream_issues)
    )

    issue_types = {issue.issue_type for issue in result.issues}
    assert "semantic_description_defect" in issue_types
    assert "naming_standard_defect" in issue_types
    assert result.defect_summary["semantic_description_defect"] >= 1
    assert result.summary


def test_health_check_returns_ok() -> None:
    assert health_check() == {"status": "ok"}

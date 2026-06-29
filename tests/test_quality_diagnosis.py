"""Smoke tests for diagnosis aggregation."""

from app.core.models.field_meta import FieldMeta
from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.skills.metadata_diagnosis_skill import (
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
        Issue(
            issue_id="issue-3",
            object_type="field",
            object_name="sales_order.transaciton_id",
            issue_type="naming_suspected_spelling_error",
            severity="low",
            evidence=["token=transaciton suggested_token=transaction"],
        ),
    ]

    result = skill.run(
        MetadataQualityDiagnosisInput(tables=[], upstream_issues=upstream_issues)
    )

    issue_types = {issue.issue_type for issue in result.issues}
    assert "missing_metadata_defect" in issue_types
    assert "naming_standard_defect" in issue_types
    assert result.defect_summary["missing_metadata_defect"] >= 1
    assert result.summary


def test_quality_diagnosis_builds_structured_findings() -> None:
    skill = MetadataQualityDiagnosisSkill()
    tables = [
        TableMeta(
            table_name="tmp_order_2022",
            table_name_cn="临时订单",
            table_description=None,
            system_name="erp",
            business_domain="order",
            fields=[
                FieldMeta(
                    field_name="cust_no",
                    field_name_cn=None,
                    field_description=None,
                    data_type="varchar",
                    nullable=False,
                    is_sensitive=True,
                )
            ],
        )
    ]

    result = skill.run(MetadataQualityDiagnosisInput(tables=tables, upstream_issues=[]))

    assert result.findings
    assert any(finding.ai_risk for finding in result.findings)
    assert any(finding.requires_manual_review for finding in result.findings)
    assert any(issue.impact_scope for issue in result.issues)


def test_health_check_returns_ok() -> None:
    assert health_check() == {"status": "ok"}

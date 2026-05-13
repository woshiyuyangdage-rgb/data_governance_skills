"""Tests for remediation planning and work-package build."""

from app.core.governance.remediation_planner import RemediationPlanner
from app.core.models.governance_gap import GovernanceGap
from app.core.models.readiness_score import ReadinessScore


def test_remediation_planner_generates_actions_from_gaps() -> None:
    readiness_scores = [
        ReadinessScore(
            object_type="table",
            object_name="sales_order",
            overall_score=0.45,
            readiness_level="not_ready",
            dimension_scores={"mapping_readiness": 0.4},
        ),
        ReadinessScore(
            object_type="overall",
            object_name="overall",
            overall_score=0.45,
            readiness_level="not_ready",
        ),
    ]
    gaps = [
        GovernanceGap(
            object_type="table",
            object_name="sales_order",
            gap_type="standard_mapping_gap",
            category="mapping",
            severity="medium",
            source_signals=["standard_mapping_missing"],
            reason="Mapping requires business review.",
            suggested_owner_role="business_data_steward",
        )
    ]

    actions = RemediationPlanner().build_actions(readiness_scores, gaps)

    assert len(actions) == 1
    assert actions[0].priority == "priority_governance"
    assert actions[0].owner_role == "business_data_steward"
    assert actions[0].expected_output == "confirmed mappings"
    assert "mapping gaps" in str(actions[0].dependency_notes)


def test_remediation_planner_builds_work_package_summary() -> None:
    readiness_scores = [
        ReadinessScore(
            object_type="overall",
            object_name="overall",
            overall_score=0.82,
            readiness_level="ready",
        )
    ]
    planner = RemediationPlanner()
    work_package = planner.build_work_package(
        readiness_scores,
        governance_gaps=[],
        remediation_actions=[],
        package_name="test_work_package",
    )

    assert work_package.package_name == "test_work_package"
    assert work_package.generated_at is not None
    assert "1 readiness scores" in str(work_package.summary)


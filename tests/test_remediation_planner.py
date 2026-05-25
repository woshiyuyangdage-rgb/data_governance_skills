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
    assert actions[0].priority_score is not None
    assert actions[0].business_impact_score is not None
    assert actions[0].ai_consumption_risk_score is not None
    assert actions[0].governance_risk_score is not None
    assert actions[0].severity_score is not None
    assert actions[0].remediation_complexity_score is not None
    assert actions[0].priority_reason is not None
    assert actions[0].suggested_cycle == "next_sprint"
    assert actions[0].expected_benefit is not None
    assert actions[0].owner_role == "business_data_steward"
    assert actions[0].expected_output == "confirmed mappings"
    assert "mapping gaps" in str(actions[0].dependency_notes)


def test_remediation_planner_sorts_by_five_dimension_priority() -> None:
    readiness_scores = [
        ReadinessScore(
            object_type="table",
            object_name="contract_core",
            overall_score=0.42,
            readiness_level="not_ready",
        ),
        ReadinessScore(
            object_type="table",
            object_name="log_archive",
            overall_score=0.92,
            readiness_level="ready",
        ),
        ReadinessScore(
            object_type="overall",
            object_name="overall",
            overall_score=0.67,
            readiness_level="partially_ready",
        ),
    ]
    gaps = [
        GovernanceGap(
            object_type="table",
            object_name="log_archive",
            gap_type="naming_standardization_gap",
            category="standardization",
            severity="low",
            source_signals=["naming_not_snake_case"],
        ),
        GovernanceGap(
            object_type="table",
            object_name="contract_core",
            gap_type="ai_consumption_risk_gap",
            category="ai",
            severity="high",
            source_signals=["ai_consumption_risk_defect", "sensitive_field"],
        ),
    ]

    actions = RemediationPlanner().build_actions(readiness_scores, gaps)

    assert actions[0].object_name == "contract_core"
    assert actions[0].priority == "priority_governance"
    assert actions[0].priority_score is not None
    assert actions[0].priority_score > 0.7
    assert actions[0].suggested_cycle == "next_sprint"
    assert "AI" in str(actions[0].expected_benefit)
    assert actions[1].object_name == "log_archive"
    assert actions[1].priority == "continuous_observation"
    assert actions[1].suggested_cycle == "routine_observation"


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

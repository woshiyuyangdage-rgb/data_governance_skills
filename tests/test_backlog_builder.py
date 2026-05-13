"""Tests for governance backlog item generation."""

from app.core.governance.backlog_builder import GovernanceBacklogBuilder
from app.core.models.governance_gap import GovernanceGap
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction


def _policies() -> dict[str, object]:
    return {
        "backlog_policy": {
            "default_status": "proposed",
            "include_dependency_notes": True,
            "include_owner_hints": True,
            "include_completion_criteria": True,
        },
        "priority_mapping": {
            "priority_governance": {"urgency_score": 3},
            "key_tracking": {"urgency_score": 2},
            "continuous_observation": {"urgency_score": 1},
        },
        "owner_role_defaults": {
            "standard_mapping_gap": "business_data_steward",
        },
    }


def test_remediation_actions_can_build_backlog_items_and_summary() -> None:
    action = RemediationAction(
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        action="Review and confirm standard mappings",
        owner_role="fallback_owner",
        priority="key_tracking",
        expected_output="confirmed standard mappings",
        dependency_notes="Requires steward review.",
        reason="Mapping confidence is low.",
    )
    gap = GovernanceGap(
        object_type="table",
        object_name="sales_order",
        gap_type="standard_mapping_gap",
        category="mapping",
        severity="medium",
        source_signals=["standard_mapping_low_confidence"],
    )
    readiness = ReadinessScore(
        object_type="table",
        object_name="sales_order",
        overall_score=0.62,
        readiness_level="partially_ready",
    )

    items, summary = GovernanceBacklogBuilder(_policies()).build_backlog(
        [action, action],
        governance_gaps=[gap],
        readiness_scores=[readiness],
    )

    assert len(items) == 1
    item = items[0]
    assert item.backlog_id.startswith("backlog_")
    assert item.object_name == "sales_order"
    assert item.status == "proposed"
    assert item.owner_role == "business_data_steward"
    assert item.priority == "key_tracking"
    assert item.urgency_score == 2
    assert item.category == "mapping"
    assert item.dependency_notes == "Requires steward review."
    assert item.completion_criteria is not None
    assert item.source_signals == ["standard_mapping_low_confidence"]
    assert summary.total_items == 1
    assert summary.by_status == {"proposed": 1}
    assert summary.by_priority == {"key_tracking": 1}
    assert summary.by_owner_role == {"business_data_steward": 1}
    assert summary.by_gap_type == {"standard_mapping_gap": 1}


def test_build_backlog_id_is_stable() -> None:
    first_id = GovernanceBacklogBuilder.build_backlog_id(
        "sales_order",
        "standard_mapping_gap",
        "Review and confirm standard mappings",
    )
    second_id = GovernanceBacklogBuilder.build_backlog_id(
        "sales_order",
        "standard_mapping_gap",
        "Review and confirm standard mappings",
    )

    assert first_id == second_id
    assert first_id.startswith("backlog_")

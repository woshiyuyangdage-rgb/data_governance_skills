"""Tests for governance portfolio aggregation."""

from app.core.governance.portfolio_aggregator import GovernancePortfolioAggregator
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.readiness_score import ReadinessScore


def _item(
    backlog_id: str,
    owner_role: str,
    status: str,
    priority: str = "key_tracking",
    gap_type: str = "standard_mapping_gap",
) -> GovernanceBacklogItem:
    return GovernanceBacklogItem(
        backlog_id=backlog_id,
        object_type="table",
        object_name=backlog_id,
        gap_type=gap_type,
        action="Review governance item",
        owner_role=owner_role,
        priority=priority,
        status=status,
    )


def test_portfolio_summary_counts_owner_workload_and_readiness_distribution() -> None:
    items = [
        _item("backlog_1", "business_data_steward", "proposed"),
        _item("backlog_2", "business_data_steward", "blocked"),
        _item("backlog_3", "metadata_manager", "completed", "priority_governance"),
    ]
    sla_statuses = [
        BacklogSlaStatus(backlog_id="backlog_1", is_overdue=True, sla_status="overdue"),
        BacklogSlaStatus(backlog_id="backlog_2", is_overdue=False, sla_status="on_track"),
        BacklogSlaStatus(backlog_id="backlog_3", is_overdue=False, sla_status="on_track"),
    ]
    readiness_scores = [
        ReadinessScore(
            object_type="table",
            object_name="sales_order",
            overall_score=0.7,
            readiness_level="partially_ready",
        ),
        ReadinessScore(
            object_type="table",
            object_name="customer",
            overall_score=0.9,
            readiness_level="ready",
        ),
    ]

    summary = GovernancePortfolioAggregator().summarize(
        items,
        readiness_scores=readiness_scores,
        backlog_sla_statuses=sla_statuses,
    )

    assert summary.total_items == 3
    assert summary.by_status == {"proposed": 1, "blocked": 1, "completed": 1}
    assert summary.by_priority == {"key_tracking": 2, "priority_governance": 1}
    assert summary.by_owner_role == {
        "business_data_steward": 2,
        "metadata_manager": 1,
    }
    assert summary.by_gap_type == {"standard_mapping_gap": 3}
    assert summary.overdue_count == 1
    assert summary.blocked_count == 1
    assert summary.readiness_distribution == {"partially_ready": 1, "ready": 1}
    assert summary.owner_workload["business_data_steward"]["open"] == 2
    assert summary.owner_workload["business_data_steward"]["blocked"] == 1
    assert summary.owner_workload["business_data_steward"]["overdue"] == 1

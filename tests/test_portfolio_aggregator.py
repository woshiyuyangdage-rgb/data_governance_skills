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
    priority_score: float | None = None,
    ai_consumption_risk_score: float | None = None,
    governance_risk_score: float | None = None,
    severity_score: float | None = None,
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
        priority_score=priority_score,
        ai_consumption_risk_score=ai_consumption_risk_score,
        governance_risk_score=governance_risk_score,
        severity_score=severity_score,
    )


def test_portfolio_summary_counts_owner_workload_and_readiness_distribution() -> None:
    items = [
        _item(
            "backlog_1",
            "business_data_steward",
            "proposed",
            priority_score=0.62,
            ai_consumption_risk_score=0.58,
            governance_risk_score=0.61,
            severity_score=0.72,
        ),
        _item(
            "backlog_2",
            "business_data_steward",
            "blocked",
            priority_score=0.78,
            ai_consumption_risk_score=0.86,
            governance_risk_score=0.73,
            severity_score=0.95,
        ),
        _item(
            "backlog_3",
            "metadata_manager",
            "completed",
            "priority_governance",
            priority_score=0.88,
            ai_consumption_risk_score=0.74,
            governance_risk_score=0.70,
            severity_score=0.95,
        ),
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
    assert summary.high_risk_item_count == 1
    assert summary.critical_risk_item_count == 2
    assert summary.avg_priority_score == 0.76
    assert summary.avg_ai_consumption_risk_score == 0.7267
    assert summary.risk_tier_distribution == {"high": 1, "critical": 2}
    assert summary.top_risk_items[0]["backlog_id"] == "backlog_2"
    assert summary.top_risk_items[0]["risk_score"] == 0.95
    assert summary.readiness_distribution == {"partially_ready": 1, "ready": 1}
    assert summary.owner_workload["business_data_steward"]["open"] == 2
    assert summary.owner_workload["business_data_steward"]["blocked"] == 1
    assert summary.owner_workload["business_data_steward"]["overdue"] == 1

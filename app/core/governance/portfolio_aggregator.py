"""Aggregate backlog, SLA, and readiness into a portfolio summary."""

from collections import Counter
from typing import Any

from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_portfolio_summary import GovernancePortfolioSummary
from app.core.models.readiness_score import ReadinessScore
from app.core.rules.config_loader import get_governance_portfolio_policies_config


class GovernancePortfolioAggregator:
    """Build portfolio-level summaries from local governance backlog signals."""

    def __init__(self, policies: dict[str, Any] | None = None) -> None:
        self.policies = policies or get_governance_portfolio_policies_config()

    @staticmethod
    def _sla_lookup(
        backlog_sla_statuses: list[BacklogSlaStatus] | None,
    ) -> dict[str, BacklogSlaStatus]:
        return {status.backlog_id: status for status in backlog_sla_statuses or []}

    @staticmethod
    def _readiness_distribution(
        readiness_scores: list[ReadinessScore] | None,
    ) -> dict[str, int]:
        return dict(Counter(score.readiness_level for score in readiness_scores or []))

    @staticmethod
    def _owner_workload(
        items: list[GovernanceBacklogItem],
        sla_lookup: dict[str, BacklogSlaStatus],
    ) -> dict[str, dict[str, int]]:
        workload: dict[str, dict[str, int]] = {}
        for item in items:
            owner = item.owner_role or "unassigned"
            owner_payload = workload.setdefault(
                owner,
                {
                    "total": 0,
                    "open": 0,
                    "blocked": 0,
                    "completed": 0,
                    "overdue": 0,
                },
            )
            owner_payload["total"] += 1
            if item.status == "completed":
                owner_payload["completed"] += 1
            elif item.status not in {"dropped"}:
                owner_payload["open"] += 1
            if item.status == "blocked":
                owner_payload["blocked"] += 1
            sla_status = sla_lookup.get(item.backlog_id)
            if sla_status is not None and sla_status.is_overdue:
                owner_payload["overdue"] += 1
        return workload

    def summarize(
        self,
        governance_backlog_items: list[GovernanceBacklogItem],
        readiness_scores: list[ReadinessScore] | None = None,
        backlog_sla_statuses: list[BacklogSlaStatus] | None = None,
    ) -> GovernancePortfolioSummary:
        """Aggregate local backlog and readiness signals into a portfolio summary."""
        by_status = Counter(item.status for item in governance_backlog_items)
        by_priority = Counter(item.priority for item in governance_backlog_items)
        by_owner_role = Counter(item.owner_role for item in governance_backlog_items)
        by_gap_type = Counter(item.gap_type for item in governance_backlog_items)
        sla_lookup = self._sla_lookup(backlog_sla_statuses)
        overdue_count = sum(1 for status in sla_lookup.values() if status.is_overdue)
        blocked_count = int(by_status.get("blocked", 0))
        readiness_distribution = self._readiness_distribution(readiness_scores)
        owner_workload = self._owner_workload(governance_backlog_items, sla_lookup)

        return GovernancePortfolioSummary(
            total_items=len(governance_backlog_items),
            by_status=dict(by_status),
            by_priority=dict(by_priority),
            by_owner_role=dict(by_owner_role),
            by_gap_type=dict(by_gap_type),
            readiness_distribution=readiness_distribution,
            overdue_count=overdue_count,
            blocked_count=blocked_count,
            owner_workload=owner_workload,
            summary=(
                f"Portfolio contains {len(governance_backlog_items)} backlog items, "
                f"{blocked_count} blocked and {overdue_count} overdue."
            ),
        )


# TODO: extend portfolio aggregation with KPI dashboard metrics and trend analytics.

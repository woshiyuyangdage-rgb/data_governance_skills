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

    @staticmethod
    def _average(values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    @staticmethod
    def _risk_score(item: GovernanceBacklogItem) -> float:
        score_parts = [
            item.priority_score,
            item.ai_consumption_risk_score,
            item.governance_risk_score,
            item.severity_score,
        ]
        scores = [
            float(score)
            for score in score_parts
            if isinstance(score, (int, float))
        ]
        if scores:
            return round(max(scores), 4)
        if item.priority == "priority_governance":
            return 0.75
        if item.priority == "key_tracking":
            return 0.55
        return 0.35

    @classmethod
    def _risk_tier(cls, item: GovernanceBacklogItem) -> str:
        risk_score = cls._risk_score(item)
        if risk_score >= 0.85:
            return "critical"
        if risk_score >= 0.70:
            return "high"
        if risk_score >= 0.50:
            return "medium"
        return "low"

    @classmethod
    def _top_risk_items(
        cls,
        items: list[GovernanceBacklogItem],
        *,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        ranked = sorted(
            items,
            key=lambda item: (
                -cls._risk_score(item),
                item.status == "completed",
                item.object_name,
                item.gap_type,
            ),
        )
        return [
            {
                "backlog_id": item.backlog_id,
                "object_name": item.object_name,
                "gap_type": item.gap_type,
                "priority": item.priority,
                "status": item.status,
                "owner_role": item.owner_role,
                "risk_score": cls._risk_score(item),
            }
            for item in ranked[:limit]
        ]

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
        priority_scores = [
            float(item.priority_score)
            for item in governance_backlog_items
            if isinstance(item.priority_score, (int, float))
        ]
        ai_risk_scores = [
            float(item.ai_consumption_risk_score)
            for item in governance_backlog_items
            if isinstance(item.ai_consumption_risk_score, (int, float))
        ]
        risk_tiers = Counter(
            self._risk_tier(item) for item in governance_backlog_items
        )
        high_risk_item_count = int(risk_tiers.get("high", 0))
        critical_risk_item_count = int(risk_tiers.get("critical", 0))
        top_risk_items = self._top_risk_items(governance_backlog_items)

        return GovernancePortfolioSummary(
            total_items=len(governance_backlog_items),
            by_status=dict(by_status),
            by_priority=dict(by_priority),
            by_owner_role=dict(by_owner_role),
            by_gap_type=dict(by_gap_type),
            readiness_distribution=readiness_distribution,
            overdue_count=overdue_count,
            blocked_count=blocked_count,
            high_risk_item_count=high_risk_item_count,
            critical_risk_item_count=critical_risk_item_count,
            avg_priority_score=self._average(priority_scores),
            avg_ai_consumption_risk_score=self._average(ai_risk_scores),
            risk_tier_distribution=dict(risk_tiers),
            top_risk_items=top_risk_items,
            owner_workload=owner_workload,
            summary=(
                f"Portfolio contains {len(governance_backlog_items)} backlog items, "
                f"{blocked_count} blocked, {overdue_count} overdue, "
                f"{critical_risk_item_count} critical risk and "
                f"{high_risk_item_count} high risk."
            ),
        )


# TODO: extend portfolio aggregation with KPI dashboard metrics and trend analytics.

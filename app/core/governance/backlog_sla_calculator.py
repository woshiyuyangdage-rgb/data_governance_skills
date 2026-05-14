"""Compute SLA-ready metadata for governance backlog items."""

from datetime import date, datetime, timedelta
from typing import Any

from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.rules.config_loader import get_backlog_sla_policies_config
from app.core.utils.time_utils import utc_today


def _today() -> date:
    return utc_today()


class BacklogSlaCalculator:
    """Infer due dates, aging, and SLA status from local backlog policies."""

    def __init__(
        self,
        policies: dict[str, Any] | None = None,
        reference_date: date | None = None,
    ) -> None:
        self.policies = policies or get_backlog_sla_policies_config()
        self.reference_date = reference_date or _today()

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        if not value:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return date.fromisoformat(text[:10])
            except ValueError:
                return None

    def infer_due_days(self, item: GovernanceBacklogItem) -> int:
        """Infer due days from priority with owner-role adjustment."""
        defaults = self.policies.get("default_due_days_by_priority", {})
        due_days = 14
        if isinstance(defaults, dict):
            configured = defaults.get(item.priority)
            if isinstance(configured, (int, float)):
                due_days = int(configured)

        adjustments = self.policies.get("owner_role_due_day_adjustments", {})
        if isinstance(adjustments, dict):
            adjustment = adjustments.get(item.owner_role)
            if isinstance(adjustment, (int, float)):
                due_days += int(adjustment)
        return max(0, due_days)

    def _created_date(self, item: GovernanceBacklogItem) -> date:
        return self._parse_date(item.created_at) or self.reference_date

    def compute_age_days(self, item: GovernanceBacklogItem) -> int:
        """Compute backlog item age in days."""
        return max(0, (self.reference_date - self._created_date(item)).days)

    def due_date_for_item(self, item: GovernanceBacklogItem) -> date:
        """Compute inferred due date."""
        return self._created_date(item) + timedelta(days=self.infer_due_days(item))

    def compute_overdue_days(self, item: GovernanceBacklogItem) -> int:
        """Compute overdue days for open backlog items."""
        if item.status in {"completed", "dropped"}:
            return 0
        due_date = self.due_date_for_item(item)
        return max(0, (self.reference_date - due_date).days)

    def infer_sla_status(self, item: GovernanceBacklogItem) -> str:
        """Infer SLA status as on_track, warning, or overdue."""
        if item.status in {"completed", "dropped"}:
            return "on_track"

        overdue_days = self.compute_overdue_days(item)
        if overdue_days > int(
            self.policies.get("overdue_policy", {}).get("overdue_after_days", 0)
            if isinstance(self.policies.get("overdue_policy", {}), dict)
            else 0
        ):
            return "overdue"

        overdue_policy = self.policies.get("overdue_policy", {})
        warn_after_days = (
            int(overdue_policy.get("warn_after_days", 3))
            if isinstance(overdue_policy, dict)
            and isinstance(overdue_policy.get("warn_after_days", 3), (int, float))
            else 3
        )
        days_until_due = (self.due_date_for_item(item) - self.reference_date).days
        if 0 <= days_until_due <= warn_after_days:
            return "warning"
        return "on_track"

    def calculate_item_status(self, item: GovernanceBacklogItem) -> BacklogSlaStatus:
        """Calculate SLA metadata for one backlog item."""
        due_date = self.due_date_for_item(item)
        overdue_days = self.compute_overdue_days(item)
        sla_status = self.infer_sla_status(item)
        return BacklogSlaStatus(
            backlog_id=item.backlog_id,
            due_date=due_date.isoformat(),
            age_days=self.compute_age_days(item),
            overdue_days=overdue_days,
            is_overdue=sla_status == "overdue",
            sla_status=sla_status,
        )

    def calculate(
        self,
        governance_backlog_items: list[GovernanceBacklogItem],
    ) -> list[BacklogSlaStatus]:
        """Calculate SLA statuses for a backlog item list."""
        return [self.calculate_item_status(item) for item in governance_backlog_items]


# TODO: extend SLA policy with business calendars and portfolio-level KPI thresholds.

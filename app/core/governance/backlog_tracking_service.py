"""Service layer for governance backlog build, persistence, and status tracking."""

from typing import Any

import app.core.governance.backlog_store as backlog_store
from app.core.governance.backlog_builder import GovernanceBacklogBuilder
from app.core.governance.backlog_sla_calculator import BacklogSlaCalculator
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.backlog_summary import BacklogSummary
from app.core.models.backlog_update_result import BacklogUpdateResult
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.workflow_result import WorkflowResult
from app.core.rules.config_loader import (
    get_backlog_status_templates_config,
    get_governance_backlog_policies_config,
)


class GovernanceBacklogTrackingService:
    """Coordinate local governance backlog generation and tracking."""

    def __init__(
        self,
        policies: dict[str, Any] | None = None,
        status_templates: dict[str, Any] | None = None,
    ) -> None:
        self.policies = policies or get_governance_backlog_policies_config()
        self.status_templates = status_templates or get_backlog_status_templates_config()
        self.builder = GovernanceBacklogBuilder(self.policies)
        self.sla_calculator = BacklogSlaCalculator()

    def _allowed_statuses(self) -> set[str]:
        statuses = self.status_templates.get("statuses", {})
        if isinstance(statuses, dict) and statuses:
            return {str(status) for status in statuses}
        transitions = (
            self.policies.get("status_transition_policy", {})
            .get("allowed_transitions", {})
        )
        return {str(status) for status in transitions} if isinstance(transitions, dict) else set()

    def _allowed_transitions(self) -> dict[str, list[str]]:
        policy = self.policies.get("status_transition_policy", {})
        transitions = policy.get("allowed_transitions", {}) if isinstance(policy, dict) else {}
        if not isinstance(transitions, dict):
            return {}
        return {
            str(status): [str(target) for target in targets]
            for status, targets in transitions.items()
            if isinstance(targets, list)
        }

    def build_backlog_from_work_package(
        self,
        work_package: GovernanceWorkPackage | None = None,
        workflow_result: WorkflowResult | None = None,
    ) -> tuple[list[GovernanceBacklogItem], BacklogSummary]:
        """Build backlog items from a work package or workflow result."""
        if work_package is not None:
            return self.builder.build_backlog(
                work_package.remediation_actions,
                governance_gaps=work_package.governance_gaps,
                readiness_scores=work_package.readiness_scores,
            )
        if workflow_result is None:
            return [], self.builder.summarize_backlog([])
        return self.builder.build_backlog(
            workflow_result.remediation_actions,
            governance_gaps=workflow_result.governance_gaps,
            readiness_scores=workflow_result.readiness_scores,
        )

    @staticmethod
    def persist_backlog_items(
        items: list[GovernanceBacklogItem],
        append: bool = True,
    ) -> dict[str, object]:
        """Persist backlog items through the local store."""
        if append:
            return backlog_store.append_backlog_items(items)
        return backlog_store.save_backlog_items(items)

    def update_backlog_status(
        self,
        backlog_id: str,
        new_status: str,
        note: str | None = None,
    ) -> BacklogUpdateResult:
        """Validate and update a backlog status."""
        new_status = str(new_status).strip()
        if new_status not in self._allowed_statuses():
            return BacklogUpdateResult(
                backlog_id=backlog_id,
                status="invalid",
                message=f"Status '{new_status}' is not configured.",
            )

        item = backlog_store.get_backlog_item(backlog_id)
        if item is None:
            return BacklogUpdateResult(
                backlog_id=backlog_id,
                status="not_found",
                message=f"Backlog item '{backlog_id}' was not found.",
            )

        allowed = self._allowed_transitions().get(item.status, [])
        if new_status != item.status and new_status not in allowed:
            return BacklogUpdateResult(
                backlog_id=backlog_id,
                old_status=item.status,
                new_status=new_status,
                status="invalid_transition",
                message=(
                    f"Transition from '{item.status}' to '{new_status}' is not allowed."
                ),
            )
        return backlog_store.update_backlog_item_status(backlog_id, new_status, note)

    def build_sla_statuses(
        self,
        items: list[GovernanceBacklogItem] | None = None,
    ) -> list[BacklogSlaStatus]:
        """Build SLA metadata for provided or persisted backlog items."""
        resolved_items = backlog_store.list_backlog_items() if items is None else items
        return self.sla_calculator.calculate(resolved_items)

    def summarize_backlog(
        self,
        items: list[GovernanceBacklogItem] | None = None,
    ) -> BacklogSummary:
        """Summarize provided or persisted backlog items."""
        resolved_items = backlog_store.list_backlog_items() if items is None else items
        return self.builder.summarize_backlog(resolved_items)

    @staticmethod
    def filter_backlog_items(
        items: list[GovernanceBacklogItem],
        status: str | None = None,
        priority: str | None = None,
        owner_role: str | None = None,
        gap_type: str | None = None,
        overdue_only: bool = False,
        sla_status: str | None = None,
        backlog_sla_statuses: list[BacklogSlaStatus] | None = None,
    ) -> list[GovernanceBacklogItem]:
        """Filter backlog items by common dashboard fields."""
        sla_lookup = {
            item.backlog_id: item for item in backlog_sla_statuses or []
        }
        filtered: list[GovernanceBacklogItem] = []
        for item in items:
            if status and item.status != status:
                continue
            if priority and item.priority != priority:
                continue
            if owner_role and item.owner_role != owner_role:
                continue
            if gap_type and item.gap_type != gap_type:
                continue
            item_sla = sla_lookup.get(item.backlog_id)
            if overdue_only and not (item_sla is not None and item_sla.is_overdue):
                continue
            if sla_status and not (
                item_sla is not None and item_sla.sla_status == sla_status
            ):
                continue
            filtered.append(item)
        return filtered


# TODO: add due-date, SLA, and project-management adapter hooks after local tracking is stable.

"""Build governance backlog items from remediation actions."""

from collections import defaultdict
from datetime import datetime
from hashlib import sha1
from typing import Any

from app.core.models.backlog_summary import BacklogSummary
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_gap import GovernanceGap
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.rules.config_loader import get_governance_backlog_policies_config


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class GovernanceBacklogBuilder:
    """Convert remediation planning output into dashboard-ready backlog items."""

    def __init__(self, policies: dict[str, Any] | None = None) -> None:
        self.policies = policies or get_governance_backlog_policies_config()

    @staticmethod
    def build_backlog_id(object_name: str, gap_type: str, action: str) -> str:
        """Build a stable backlog id from object, gap, and action identity."""
        raw = f"{object_name}|{gap_type}|{action}".lower().strip()
        return f"backlog_{sha1(raw.encode('utf-8')).hexdigest()[:12]}"

    def _backlog_policy(self) -> dict[str, Any]:
        policy = self.policies.get("backlog_policy", {})
        return policy if isinstance(policy, dict) else {}

    def _default_status(self) -> str:
        return str(self._backlog_policy().get("default_status", "proposed"))

    def _urgency_score(self, priority: str) -> int | None:
        mapping = self.policies.get("priority_mapping", {})
        payload = mapping.get(priority, {}) if isinstance(mapping, dict) else {}
        if not isinstance(payload, dict):
            return None
        value = payload.get("urgency_score")
        return int(value) if isinstance(value, (int, float)) else None

    def _default_owner_role(self, gap_type: str, fallback: str) -> str:
        defaults = self.policies.get("owner_role_defaults", {})
        if isinstance(defaults, dict):
            configured = str(defaults.get(gap_type, "")).strip()
            if configured:
                return configured
        return fallback

    @staticmethod
    def _gap_lookup(governance_gaps: list[GovernanceGap] | None) -> dict[tuple[str, str], GovernanceGap]:
        lookup: dict[tuple[str, str], GovernanceGap] = {}
        for gap in governance_gaps or []:
            lookup[(gap.object_name, gap.gap_type)] = gap
        return lookup

    @staticmethod
    def _readiness_lookup(
        readiness_scores: list[ReadinessScore] | None,
    ) -> dict[str, ReadinessScore]:
        return {score.object_name: score for score in readiness_scores or []}

    @staticmethod
    def _completion_criteria(action: RemediationAction) -> str:
        if action.expected_output:
            return f"Expected output is available: {action.expected_output}."
        return f"Governance action completed and evidence recorded for {action.gap_type}."

    def remediation_action_to_backlog_item(
        self,
        action: RemediationAction,
        governance_gaps: list[GovernanceGap] | None = None,
        readiness_scores: list[ReadinessScore] | None = None,
    ) -> GovernanceBacklogItem:
        """Convert one remediation action into one backlog item."""
        policy = self._backlog_policy()
        gap = self._gap_lookup(governance_gaps).get((action.object_name, action.gap_type))
        score = self._readiness_lookup(readiness_scores).get(action.object_name)
        created_at = _utc_now()
        owner_role = (
            self._default_owner_role(action.gap_type, action.owner_role)
            if bool(policy.get("include_owner_hints", True))
            else action.owner_role
        )
        dependency_notes = (
            action.dependency_notes
            if bool(policy.get("include_dependency_notes", True))
            else None
        )
        completion_criteria = (
            self._completion_criteria(action)
            if bool(policy.get("include_completion_criteria", True))
            else None
        )
        reason = action.reason
        if reason is None and score is not None:
            reason = (
                f"{score.object_name} readiness is {score.readiness_level} "
                f"({score.overall_score:.2f})."
            )
        return GovernanceBacklogItem(
            backlog_id=self.build_backlog_id(
                action.object_name,
                action.gap_type,
                action.action,
            ),
            object_type=action.object_type,
            object_name=action.object_name,
            gap_type=action.gap_type,
            category=gap.category if gap is not None else None,
            action=action.action,
            owner_role=owner_role,
            priority=action.priority,
            status=self._default_status(),
            urgency_score=self._urgency_score(action.priority),
            dependency_notes=dependency_notes,
            completion_criteria=completion_criteria,
            expected_output=action.expected_output,
            reason=reason,
            source_signals=list(gap.source_signals) if gap is not None else [],
            created_at=created_at,
            updated_at=created_at,
        )

    @staticmethod
    def deduplicate_backlog_items(
        items: list[GovernanceBacklogItem],
    ) -> list[GovernanceBacklogItem]:
        """Keep one backlog item per object + gap_type + action."""
        deduped: dict[tuple[str, str, str], GovernanceBacklogItem] = {}
        for item in items:
            key = (item.object_name, item.gap_type, item.action)
            deduped.setdefault(key, item)
        return list(deduped.values())

    def build_backlog(
        self,
        remediation_actions: list[RemediationAction],
        governance_gaps: list[GovernanceGap] | None = None,
        readiness_scores: list[ReadinessScore] | None = None,
    ) -> tuple[list[GovernanceBacklogItem], BacklogSummary]:
        """Build backlog items and a summary from remediation actions."""
        items = [
            self.remediation_action_to_backlog_item(
                action,
                governance_gaps=governance_gaps,
                readiness_scores=readiness_scores,
            )
            for action in remediation_actions
        ]
        items = self.deduplicate_backlog_items(items)
        return items, self.summarize_backlog(items)

    @staticmethod
    def summarize_backlog(items: list[GovernanceBacklogItem]) -> BacklogSummary:
        """Summarize backlog counts for dashboard and report outputs."""
        by_status: dict[str, int] = defaultdict(int)
        by_priority: dict[str, int] = defaultdict(int)
        by_owner_role: dict[str, int] = defaultdict(int)
        by_gap_type: dict[str, int] = defaultdict(int)
        for item in items:
            by_status[item.status] += 1
            by_priority[item.priority] += 1
            by_owner_role[item.owner_role] += 1
            by_gap_type[item.gap_type] += 1
        blocked_count = by_status.get("blocked", 0)
        completed_count = by_status.get("completed", 0)
        return BacklogSummary(
            total_items=len(items),
            by_status=dict(by_status),
            by_priority=dict(by_priority),
            by_owner_role=dict(by_owner_role),
            by_gap_type=dict(by_gap_type),
            blocked_count=blocked_count,
            completed_count=completed_count,
            summary=(
                f"Backlog contains {len(items)} items, "
                f"{blocked_count} blocked and {completed_count} completed."
            ),
        )


# TODO: extend backlog items with due dates, SLA policy, and project-management adapter metadata.


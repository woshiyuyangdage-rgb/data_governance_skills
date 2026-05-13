"""Rule-based remediation planning."""

from datetime import datetime
from typing import Any

from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.rules.config_loader import get_remediation_templates_config

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class RemediationPlanner:
    """Turn readiness scores and classified gaps into recommended actions."""

    def __init__(self, templates: dict[str, Any] | None = None) -> None:
        self.templates = templates or get_remediation_templates_config()

    def _template_for_gap(self, gap_type: str) -> dict[str, Any]:
        templates = self.templates.get("templates", {})
        if not isinstance(templates, dict):
            return {}
        template = templates.get(gap_type, {})
        return template if isinstance(template, dict) else {}

    @staticmethod
    def _score_lookup(readiness_scores: list[ReadinessScore]) -> dict[str, ReadinessScore]:
        return {score.object_name: score for score in readiness_scores}

    @staticmethod
    def infer_priority(gap: GovernanceGap, score: ReadinessScore | None) -> str:
        """Infer remediation priority from readiness and gap severity."""
        if score is not None and (
            score.readiness_level == "not_ready" or score.overall_score < 0.5
        ):
            return "priority_governance"
        if gap.severity == "high":
            return "priority_governance"
        if score is not None and score.readiness_level == "partially_ready":
            return "key_tracking"
        if SEVERITY_RANK.get(gap.severity, 1) >= SEVERITY_RANK["medium"]:
            return "key_tracking"
        return "continuous_observation"

    @staticmethod
    def dependency_notes_for_gap(gap_type: str) -> str | None:
        """Return lightweight dependency notes for common governance gap types."""
        if gap_type == "standard_mapping_gap":
            return "Resolve mapping gaps before final quality rule confirmation."
        if gap_type == "metadata_completion_gap":
            return "Complete metadata before domain review and stewardship sign-off."
        if gap_type == "structural_standardization_gap":
            return "Confirm STG structure before downstream model or execution package use."
        if gap_type == "quality_rule_gap":
            return "Confirm quality rules before execution-ready package finalization."
        if gap_type == "review_backlog_gap":
            return "Clear manual review backlog before treating readiness as final."
        return None

    def build_actions(
        self,
        readiness_scores: list[ReadinessScore],
        governance_gaps: list[GovernanceGap],
        domain_pack_hints: dict | None = None,
    ) -> list[RemediationAction]:
        """Build remediation actions from gaps and readiness levels."""
        score_lookup = self._score_lookup(readiness_scores)
        overall_score = score_lookup.get("overall")
        owner_roles = dict((domain_pack_hints or {}).get("default_owner_roles", {}))
        actions: list[RemediationAction] = []
        for gap in governance_gaps:
            template = self._template_for_gap(gap.gap_type)
            score = score_lookup.get(gap.object_name) or overall_score
            actions.append(
                RemediationAction(
                    object_type=gap.object_type,
                    object_name=gap.object_name,
                    gap_type=gap.gap_type,
                    action=str(
                        template.get("action")
                        or f"Review and remediate {gap.gap_type}"
                    ),
                    owner_role=str(
                        template.get("owner_role")
                        or gap.suggested_owner_role
                        or owner_roles.get("remediation")
                        or "governance_lead"
                    ),
                    priority=self.infer_priority(gap, score),
                    expected_output=template.get("expected_output"),
                    dependency_notes=self.dependency_notes_for_gap(gap.gap_type),
                    reason=gap.reason,
                )
            )
        priority_rank = {
            "priority_governance": 1,
            "key_tracking": 2,
            "continuous_observation": 3,
        }
        return sorted(
            actions,
            key=lambda action: (priority_rank.get(action.priority, 99), action.object_name),
        )

    def build_work_package(
        self,
        readiness_scores: list[ReadinessScore],
        governance_gaps: list[GovernanceGap],
        remediation_actions: list[RemediationAction] | None = None,
        package_name: str = "governance_work_package",
    ) -> GovernanceWorkPackage:
        """Bundle readiness, gaps, and remediation actions."""
        actions = remediation_actions or self.build_actions(readiness_scores, governance_gaps)
        overall = next(
            (score for score in readiness_scores if score.object_type == "overall"),
            None,
        )
        summary = (
            f"Governance work package contains {len(readiness_scores)} readiness scores, "
            f"{len(governance_gaps)} gaps, and {len(actions)} remediation actions."
        )
        if overall is not None:
            summary += (
                f" Overall readiness is {overall.readiness_level} "
                f"({overall.overall_score:.2f})."
            )
        return GovernanceWorkPackage(
            package_name=package_name,
            generated_at=_utc_now(),
            readiness_scores=readiness_scores,
            governance_gaps=governance_gaps,
            remediation_actions=actions,
            summary=summary,
        )

    @staticmethod
    def summarize(
        readiness_scores: list[ReadinessScore],
        governance_gaps: list[GovernanceGap],
        remediation_actions: list[RemediationAction],
    ) -> dict[str, object]:
        """Return a compact planning summary."""
        priority_counts: dict[str, int] = {}
        owner_counts: dict[str, int] = {}
        for action in remediation_actions:
            priority_counts[action.priority] = priority_counts.get(action.priority, 0) + 1
            owner_counts[action.owner_role] = owner_counts.get(action.owner_role, 0) + 1
        overall = next(
            (score for score in readiness_scores if score.object_type == "overall"),
            None,
        )
        return {
            "readiness_score_count": len(readiness_scores),
            "gap_count": len(governance_gaps),
            "remediation_action_count": len(remediation_actions),
            "priority_counts": priority_counts,
            "owner_role_counts": owner_counts,
            "overall_score": overall.overall_score if overall else None,
            "overall_readiness_level": overall.readiness_level if overall else None,
        }


# TODO: add action tracking, owner assignment integration, and portfolio dashboards after the local work-package contract stabilizes.

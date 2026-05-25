"""Rule-based remediation planning."""

from typing import Any

from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.rules.config_loader import get_remediation_templates_config
from app.core.utils.time_utils import utc_now_seconds

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
PRIORITY_RANK = {
    "priority_governance": 1,
    "key_tracking": 2,
    "continuous_observation": 3,
}
BUSINESS_IMPACT_BY_GAP = {
    "standard_mapping_gap": 0.78,
    "semantic_consistency_gap": 0.76,
    "quality_rule_gap": 0.72,
    "ai_consumption_risk_gap": 0.86,
    "business_ownership_gap": 0.64,
    "metadata_completion_gap": 0.58,
    "structural_standardization_gap": 0.62,
    "technical_object_gap": 0.46,
    "naming_standardization_gap": 0.42,
    "review_backlog_gap": 0.68,
}
AI_RISK_BY_GAP = {
    "ai_consumption_risk_gap": 0.95,
    "semantic_consistency_gap": 0.86,
    "standard_mapping_gap": 0.82,
    "metadata_completion_gap": 0.74,
    "quality_rule_gap": 0.64,
    "business_ownership_gap": 0.58,
    "technical_object_gap": 0.56,
    "structural_standardization_gap": 0.52,
    "naming_standardization_gap": 0.45,
    "review_backlog_gap": 0.62,
}
GOVERNANCE_RISK_BY_GAP = {
    "quality_rule_gap": 0.82,
    "ai_consumption_risk_gap": 0.84,
    "standard_mapping_gap": 0.78,
    "business_ownership_gap": 0.76,
    "semantic_consistency_gap": 0.74,
    "technical_object_gap": 0.68,
    "metadata_completion_gap": 0.58,
    "structural_standardization_gap": 0.54,
    "review_backlog_gap": 0.66,
    "naming_standardization_gap": 0.42,
}
COMPLEXITY_BY_GAP = {
    "metadata_completion_gap": 0.25,
    "naming_standardization_gap": 0.38,
    "technical_object_gap": 0.36,
    "quality_rule_gap": 0.48,
    "standard_mapping_gap": 0.55,
    "semantic_consistency_gap": 0.58,
    "ai_consumption_risk_gap": 0.62,
    "structural_standardization_gap": 0.68,
    "business_ownership_gap": 0.70,
    "review_backlog_gap": 0.32,
}
PRIORITY_WEIGHTS = {
    "business_impact": 0.24,
    "ai_consumption_risk": 0.24,
    "governance_risk": 0.20,
    "severity": 0.20,
    "remediation_complexity": 0.12,
}


def _utc_now() -> str:
    return utc_now_seconds()


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
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, round(value, 4)))

    @staticmethod
    def severity_score(severity: str) -> float:
        return {
            "high": 0.95,
            "medium": 0.65,
            "low": 0.35,
        }.get(str(severity or "").strip().lower(), 0.45)

    @staticmethod
    def readiness_risk(score: ReadinessScore | None) -> float:
        if score is None:
            return 0.50
        return RemediationPlanner._clamp(1.0 - float(score.overall_score))

    @staticmethod
    def _signal_boost(signals: list[str], keywords: set[str]) -> float:
        signal_text = " ".join(signals).lower()
        return 0.12 if any(keyword in signal_text for keyword in keywords) else 0.0

    @classmethod
    def priority_dimensions(
        cls,
        gap: GovernanceGap,
        score: ReadinessScore | None,
    ) -> dict[str, float]:
        """Compute the five governance-priority dimensions."""
        readiness_risk = cls.readiness_risk(score)
        business_impact = BUSINESS_IMPACT_BY_GAP.get(gap.gap_type, 0.50)
        business_impact += readiness_risk * 0.20
        business_impact += cls._signal_boost(
            gap.source_signals,
            {"customer", "contract", "amount", "transaction", "sensitive"},
        )

        ai_risk = AI_RISK_BY_GAP.get(gap.gap_type, 0.50)
        ai_risk += readiness_risk * 0.18
        ai_risk += cls._signal_boost(
            gap.source_signals,
            {"ai", "rag", "text_to_sql", "semantic", "description", "mapping"},
        )

        governance_risk = GOVERNANCE_RISK_BY_GAP.get(gap.gap_type, 0.50)
        governance_risk += cls._signal_boost(
            gap.source_signals,
            {"sensitive", "privacy", "amount", "quality", "manual_review"},
        )

        severity = cls.severity_score(gap.severity)
        complexity = COMPLEXITY_BY_GAP.get(gap.gap_type, 0.50)
        return {
            "business_impact_score": cls._clamp(business_impact),
            "ai_consumption_risk_score": cls._clamp(ai_risk),
            "governance_risk_score": cls._clamp(governance_risk),
            "severity_score": cls._clamp(severity),
            "remediation_complexity_score": cls._clamp(complexity),
        }

    @classmethod
    def priority_score(
        cls,
        gap: GovernanceGap,
        score: ReadinessScore | None,
    ) -> float:
        dimensions = cls.priority_dimensions(gap, score)
        weighted = (
            dimensions["business_impact_score"] * PRIORITY_WEIGHTS["business_impact"]
            + dimensions["ai_consumption_risk_score"]
            * PRIORITY_WEIGHTS["ai_consumption_risk"]
            + dimensions["governance_risk_score"]
            * PRIORITY_WEIGHTS["governance_risk"]
            + dimensions["severity_score"] * PRIORITY_WEIGHTS["severity"]
            + (1.0 - dimensions["remediation_complexity_score"])
            * PRIORITY_WEIGHTS["remediation_complexity"]
        )
        return cls._clamp(weighted)

    @staticmethod
    def priority_from_score(score: float, complexity: float) -> str:
        if score >= 0.70 and complexity <= 0.72:
            return "priority_governance"
        if score >= 0.52:
            return "key_tracking"
        return "continuous_observation"

    @staticmethod
    def infer_priority(gap: GovernanceGap, score: ReadinessScore | None) -> str:
        """Infer remediation priority from five-dimensional governance scoring."""
        dimensions = RemediationPlanner.priority_dimensions(gap, score)
        return RemediationPlanner.priority_from_score(
            RemediationPlanner.priority_score(gap, score),
            dimensions["remediation_complexity_score"],
        )

    @staticmethod
    def suggested_cycle(priority: str) -> str:
        return {
            "priority_governance": "next_sprint",
            "key_tracking": "next_1_to_2_cycles",
            "continuous_observation": "routine_observation",
        }.get(priority, "next_1_to_2_cycles")

    @staticmethod
    def expected_benefit_for_gap(gap_type: str) -> str:
        return {
            "metadata_completion_gap": "Improve catalog usability and AI context completeness.",
            "standard_mapping_gap": "Improve semantic consistency for RAG and Text-to-SQL.",
            "semantic_consistency_gap": "Reduce incorrect interpretation by business users and AI assistants.",
            "ai_consumption_risk_gap": "Reduce AI misuse, wrong retrieval, and sensitive-data exposure risk.",
            "quality_rule_gap": "Improve data trust before automated checks and rule execution.",
            "structural_standardization_gap": "Stabilize downstream STG modeling and execution package use.",
            "technical_object_gap": "Reduce catalog pollution and accidental AI retrieval of technical assets.",
            "business_ownership_gap": "Clarify accountability and review routing.",
            "review_backlog_gap": "Unblock governance decisions waiting for human confirmation.",
            "naming_standardization_gap": "Improve scanability and downstream engineering consistency.",
        }.get(gap_type, "Improve governance reliability and AI-ready consumption.")

    @staticmethod
    def priority_reason_for(
        gap: GovernanceGap,
        score: ReadinessScore | None,
        priority_score: float,
        dimensions: dict[str, float],
    ) -> str:
        readiness = (
            f"readiness={score.overall_score:.2f}/{score.readiness_level}"
            if score is not None
            else "readiness=N/A"
        )
        return (
            f"{readiness}; severity={gap.severity}; "
            f"business_impact={dimensions['business_impact_score']:.2f}; "
            f"ai_risk={dimensions['ai_consumption_risk_score']:.2f}; "
            f"governance_risk={dimensions['governance_risk_score']:.2f}; "
            f"complexity={dimensions['remediation_complexity_score']:.2f}; "
            f"priority_score={priority_score:.2f}."
        )

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
            dimensions = self.priority_dimensions(gap, score)
            priority_score = self.priority_score(gap, score)
            priority = self.priority_from_score(
                priority_score,
                dimensions["remediation_complexity_score"],
            )
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
                    priority=priority,
                    priority_score=priority_score,
                    business_impact_score=dimensions["business_impact_score"],
                    ai_consumption_risk_score=dimensions[
                        "ai_consumption_risk_score"
                    ],
                    governance_risk_score=dimensions["governance_risk_score"],
                    severity_score=dimensions["severity_score"],
                    remediation_complexity_score=dimensions[
                        "remediation_complexity_score"
                    ],
                    priority_reason=self.priority_reason_for(
                        gap,
                        score,
                        priority_score,
                        dimensions,
                    ),
                    suggested_cycle=self.suggested_cycle(priority),
                    expected_benefit=self.expected_benefit_for_gap(gap.gap_type),
                    expected_output=template.get("expected_output"),
                    dependency_notes=self.dependency_notes_for_gap(gap.gap_type),
                    reason=gap.reason,
                )
            )
        return sorted(
            actions,
            key=lambda action: (
                PRIORITY_RANK.get(action.priority, 99),
                -(action.priority_score or 0.0),
                action.object_name,
            ),
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
        priority_counts = self.summarize(
            readiness_scores,
            governance_gaps,
            actions,
        )["priority_counts"]
        if priority_counts:
            summary += f" Priority distribution: {priority_counts}."
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
        avg_priority_score = (
            round(
                sum(action.priority_score or 0.0 for action in remediation_actions)
                / len(remediation_actions),
                4,
            )
            if remediation_actions
            else 0.0
        )
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
            "avg_priority_score": avg_priority_score,
            "overall_score": overall.overall_score if overall else None,
            "overall_readiness_level": overall.readiness_level if overall else None,
        }


# TODO: add action tracking, owner assignment integration, and portfolio dashboards after the local work-package contract stabilizes.

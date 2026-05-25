"""Governance, backlog, portfolio, and review dataframe helpers."""

import pandas as pd

from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.backlog_sla_status import BacklogSlaStatus
from app.core.models.backlog_summary import BacklogSummary
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.governance_gap import GovernanceGap
from app.core.models.governance_portfolio_summary import GovernancePortfolioSummary
from app.core.models.governance_work_package import GovernanceWorkPackage
from app.core.models.progress_snapshot import ProgressSnapshot
from app.core.models.readiness_score import ReadinessScore
from app.core.models.remediation_action import RemediationAction
from app.core.models.review_summary import ReviewSummary


def readiness_scores_to_dataframe(
    readiness_scores: list[ReadinessScore],
) -> pd.DataFrame:
    """Convert readiness scores to a stable dataframe."""
    records = []
    for score in readiness_scores:
        payload = {
            "object_type": score.object_type,
            "object_name": score.object_name,
            "overall_score": score.overall_score,
            "readiness_level": score.readiness_level,
            "summary": score.summary,
        }
        for key, value in score.dimension_scores.items():
            payload[key] = value
        records.append(payload)
    return pd.DataFrame(records)


def ai_ready_scores_to_dataframe(
    ai_ready_scores: list[AiReadyScore],
) -> pd.DataFrame:
    """Convert AI-ready scores to a stable dataframe."""
    records = []
    for score in ai_ready_scores:
        payload = {
            "object_type": score.object_type,
            "object_name": score.object_name,
            "overall_score": score.overall_score,
            "ai_ready_level": score.ai_ready_level,
            "summary": score.summary,
            "evidence_joined": " | ".join(score.evidence),
            "risk_flags_joined": " | ".join(score.risk_flags),
            "recommended_actions_joined": " | ".join(score.recommended_actions),
        }
        for key, value in score.dimension_scores.items():
            payload[key] = value
        records.append(payload)
    return pd.DataFrame(records)


def governance_gaps_to_dataframe(
    governance_gaps: list[GovernanceGap],
) -> pd.DataFrame:
    """Convert governance gaps to a stable dataframe."""
    records = []
    for gap in governance_gaps:
        records.append(
            {
                "object_type": gap.object_type,
                "object_name": gap.object_name,
                "gap_type": gap.gap_type,
                "category": gap.category,
                "severity": gap.severity,
                "source_signals": gap.source_signals,
                "reason": gap.reason,
                "suggested_owner_role": gap.suggested_owner_role,
            }
        )
    return pd.DataFrame(records)


def remediation_actions_to_dataframe(
    remediation_actions: list[RemediationAction],
) -> pd.DataFrame:
    """Convert remediation actions to a stable dataframe."""
    records = []
    for action in remediation_actions:
        records.append(
            {
                "object_type": action.object_type,
                "object_name": action.object_name,
                "gap_type": action.gap_type,
                "action": action.action,
                "owner_role": action.owner_role,
                "priority": action.priority,
                "priority_score": action.priority_score,
                "business_impact_score": action.business_impact_score,
                "ai_consumption_risk_score": action.ai_consumption_risk_score,
                "governance_risk_score": action.governance_risk_score,
                "severity_score": action.severity_score,
                "remediation_complexity_score": action.remediation_complexity_score,
                "priority_reason": action.priority_reason,
                "suggested_cycle": action.suggested_cycle,
                "expected_benefit": action.expected_benefit,
                "expected_output": action.expected_output,
                "dependency_notes": action.dependency_notes,
                "reason": action.reason,
            }
        )
    return pd.DataFrame(records)


def governance_work_package_summary_to_dataframe(
    work_package: GovernanceWorkPackage | None,
    readiness_summary: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Convert governance work package metadata into a one-row dataframe."""
    if work_package is None and not readiness_summary:
        return pd.DataFrame()
    payload = dict(readiness_summary or {})
    if work_package is not None:
        payload.update(
            {
                "package_name": work_package.package_name,
                "generated_at": work_package.generated_at,
                "readiness_score_count": len(work_package.readiness_scores),
                "gap_count": len(work_package.governance_gaps),
                "remediation_action_count": len(work_package.remediation_actions),
                "summary": work_package.summary,
            }
        )
    return pd.DataFrame([payload])


def governance_backlog_items_to_dataframe(
    backlog_items: list[GovernanceBacklogItem],
) -> pd.DataFrame:
    """Convert governance backlog items to a stable dataframe."""
    records = []
    for item in backlog_items:
        records.append(
            {
                "backlog_id": item.backlog_id,
                "object_type": item.object_type,
                "object_name": item.object_name,
                "gap_type": item.gap_type,
                "category": item.category,
                "action": item.action,
                "owner_role": item.owner_role,
                "priority": item.priority,
                "priority_score": item.priority_score,
                "business_impact_score": item.business_impact_score,
                "ai_consumption_risk_score": item.ai_consumption_risk_score,
                "governance_risk_score": item.governance_risk_score,
                "severity_score": item.severity_score,
                "remediation_complexity_score": item.remediation_complexity_score,
                "priority_reason": item.priority_reason,
                "suggested_cycle": item.suggested_cycle,
                "expected_benefit": item.expected_benefit,
                "status": item.status,
                "urgency_score": item.urgency_score,
                "dependency_notes": item.dependency_notes,
                "blocked_by": item.blocked_by,
                "completion_criteria": item.completion_criteria,
                "expected_output": item.expected_output,
                "reason": item.reason,
                "source_signals": item.source_signals,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "notes": item.notes,
            }
        )
    return pd.DataFrame(records)


def backlog_summary_to_dataframe(
    backlog_summary: BacklogSummary | None,
) -> pd.DataFrame:
    """Convert backlog summary into a one-row dataframe."""
    if backlog_summary is None:
        return pd.DataFrame()
    return pd.DataFrame([backlog_summary.model_dump()])


def backlog_sla_statuses_to_dataframe(
    statuses: list[BacklogSlaStatus],
) -> pd.DataFrame:
    """Convert backlog SLA statuses to a stable dataframe."""
    return pd.DataFrame([status.model_dump() for status in statuses])


def governance_portfolio_summary_to_dataframe(
    summary: GovernancePortfolioSummary | None,
) -> pd.DataFrame:
    """Convert governance portfolio summary into a one-row dataframe."""
    if summary is None:
        return pd.DataFrame()
    return pd.DataFrame([summary.model_dump()])


def progress_snapshot_to_dataframe(
    snapshot: ProgressSnapshot | None,
) -> pd.DataFrame:
    """Convert a progress snapshot into a one-row dataframe."""
    if snapshot is None:
        return pd.DataFrame()
    return pd.DataFrame([snapshot.model_dump()])


def review_summary_to_dataframe(review_summary: ReviewSummary | None) -> pd.DataFrame:
    """Convert a review summary into a one-row dataframe."""
    if review_summary is None:
        return pd.DataFrame()

    return pd.DataFrame(
        [
            {
                "accepted_count": review_summary.accepted_count,
                "rejected_count": review_summary.rejected_count,
                "edited_count": review_summary.edited_count,
                "manual_review_count": review_summary.manual_review_count,
                "total_reviewed_count": review_summary.total_reviewed_count,
            }
        ]
    )

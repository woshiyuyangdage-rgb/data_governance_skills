"""Markdown report governance section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_governance_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Governance Readiness Assessment", ""]
    if result.readiness_scores:
        for score in result.readiness_scores:
            lines.append(
                f"- `{score.object_type}:{score.object_name}` | "
                f"score={score.overall_score:.2f} | level={score.readiness_level} | "
                f"summary={score.summary or 'N/A'}"
            )
    else:
        lines.append("- No governance readiness scores available.")

    lines.extend(["", "# Governance Gaps", ""])
    if result.governance_gaps:
        for gap in result.governance_gaps:
            lines.append(
                f"- `{gap.object_name}` | {gap.gap_type} | category={gap.category} | "
                f"severity={gap.severity} | owner={gap.suggested_owner_role or 'N/A'} | "
                f"signals={', '.join(gap.source_signals) or 'N/A'}"
            )
    else:
        lines.append("- No governance gaps available.")

    lines.extend(["", "# Remediation Plan", ""])
    if result.remediation_actions:
        for action in result.remediation_actions:
            lines.append(
                f"- `{action.object_name}` | priority={action.priority} | "
                f"owner={action.owner_role} | gap={action.gap_type} | "
                f"action={action.action}"
            )
    else:
        lines.append("- No remediation actions available.")

    lines.extend(["", "# Governance Work Package", ""])
    if result.governance_work_package is not None:
        work_package = result.governance_work_package
        lines.append(f"- Package name: `{work_package.package_name}`")
        lines.append(f"- Generated at: {work_package.generated_at or 'N/A'}")
        lines.append(f"- Readiness scores: {len(work_package.readiness_scores)}")
        lines.append(f"- Governance gaps: {len(work_package.governance_gaps)}")
        lines.append(f"- Remediation actions: {len(work_package.remediation_actions)}")
        lines.append(f"- Summary: {work_package.summary or 'N/A'}")
    else:
        lines.append("- No governance work package available.")

    lines.extend(["", "# Governance Backlog", ""])
    if result.governance_backlog_items:
        for item in result.governance_backlog_items:
            lines.append(
                f"- `{item.backlog_id}` | `{item.object_name}` | "
                f"gap={item.gap_type} | status={item.status} | "
                f"priority={item.priority} | owner={item.owner_role} | "
                f"action={item.action}"
            )
    else:
        lines.append("- No governance backlog items available.")

    lines.extend(["", "# Backlog Summary", ""])
    if result.backlog_summary is not None:
        summary = result.backlog_summary
        lines.append(f"- Total items: {summary.total_items}")
        lines.append(f"- By status: {summary.by_status}")
        lines.append(f"- By priority: {summary.by_priority}")
        lines.append(f"- By owner role: {summary.by_owner_role}")
        lines.append(f"- By gap type: {summary.by_gap_type}")
        lines.append(f"- Blocked count: {summary.blocked_count}")
        lines.append(f"- Completed count: {summary.completed_count}")
        lines.append(f"- Summary: {summary.summary or 'N/A'}")
    else:
        lines.append("- No backlog summary available.")

    lines.extend(["", "# Backlog SLA Status", ""])
    if result.backlog_sla_statuses:
        for status in result.backlog_sla_statuses:
            lines.append(
                f"- `{status.backlog_id}` | due={status.due_date or 'N/A'} | "
                f"age_days={status.age_days if status.age_days is not None else 'N/A'} | "
                f"overdue_days={status.overdue_days if status.overdue_days is not None else 'N/A'} | "
                f"sla_status={status.sla_status or 'N/A'}"
            )
    else:
        lines.append("- No backlog SLA statuses available.")

    lines.extend(["", "# Governance Portfolio Summary", ""])
    if result.governance_portfolio_summary is not None:
        portfolio = result.governance_portfolio_summary
        lines.append(f"- Total items: {portfolio.total_items}")
        lines.append(f"- By status: {portfolio.by_status}")
        lines.append(f"- By priority: {portfolio.by_priority}")
        lines.append(f"- By owner role: {portfolio.by_owner_role}")
        lines.append(f"- By gap type: {portfolio.by_gap_type}")
        lines.append(f"- Readiness distribution: {portfolio.readiness_distribution}")
        lines.append(f"- Overdue count: {portfolio.overdue_count}")
        lines.append(f"- Blocked count: {portfolio.blocked_count}")
        lines.append(f"- Owner workload: {portfolio.owner_workload}")
        lines.append(f"- Summary: {portfolio.summary or 'N/A'}")
    else:
        lines.append("- No governance portfolio summary available.")

    lines.extend(["", "# Progress Snapshot", ""])
    if result.progress_snapshot is not None:
        snapshot = result.progress_snapshot
        lines.append(f"- Snapshot ID: `{snapshot.snapshot_id}`")
        lines.append(f"- Generated at: {snapshot.generated_at or 'N/A'}")
        lines.append(f"- Total backlog items: {snapshot.total_backlog_items}")
        lines.append(f"- Completed count: {snapshot.completed_count}")
        lines.append(f"- Blocked count: {snapshot.blocked_count}")
        lines.append(f"- Overdue count: {snapshot.overdue_count}")
        lines.append(f"- Average readiness score: {snapshot.avg_readiness_score}")
        lines.append(f"- Notes: {snapshot.notes or 'N/A'}")
    else:
        lines.append("- No progress snapshot available.")
    return lines


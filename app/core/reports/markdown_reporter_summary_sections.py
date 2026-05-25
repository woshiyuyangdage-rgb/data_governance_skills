"""Markdown report summary section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_project_summary(result: WorkflowResult) -> list[str]:
    lines = [
        "# Project Run Summary",
        "",
        f"- Status: `{result.status}`",
        f"- Message: {result.message or 'N/A'}",
        f"- Input table count: {result.input_table_count}",
        f"- Issue count: {result.issue_count}",
        f"- Task count: {result.task_count}",
        "",
        "# Input Overview",
        "",
        "This report was generated from the local metadata governance MVP pipeline.",
        "",
        "# Skill Summaries",
        "",
    ]
    if result.skill_outputs:
        for skill_name, payload in result.skill_outputs.items():
            summary = (
                payload.get("summary", "No summary available.")
                if isinstance(payload, dict)
                else "No summary available."
            )
            lines.append(f"- **{skill_name}**: {summary}")
    else:
        lines.append("- No skill outputs available.")
    return lines


def build_diagnosis_issues_section(result: WorkflowResult) -> list[str]:
    lines = ["", "# Diagnosis Issues", ""]
    if result.issues:
        for issue in result.issues:
            evidence = "; ".join(issue.evidence[:3]) if issue.evidence else "N/A"
            lines.append(
                f"- `{issue.issue_id}` | {issue.object_type} | `{issue.object_name}` | "
                f"{issue.issue_type} | severity={issue.severity} | "
                f"priority={issue.recommended_priority or 'N/A'} | "
                f"ai_risk={issue.ai_risk or 'N/A'} | "
                f"manual_review={issue.requires_manual_review if issue.requires_manual_review is not None else 'N/A'} | "
                f"evidence={evidence}"
            )
    else:
        lines.append("- No issues generated.")
    return lines


def build_governance_tasks_section(result: WorkflowResult) -> list[str]:
    lines = ["", "# Governance Tasks", ""]
    if result.tasks:
        for task in result.tasks:
            issue_ids = ", ".join(task.issue_ids)
            lines.append(
                f"- `{task.task_id}` | priority={task.priority} | owner={task.suggested_owner_role or 'N/A'} | "
                f"issues={issue_ids} | action={task.action}"
            )
    else:
        lines.append("- No tasks generated.")
    return lines

"""Markdown report section builders."""

from app.core.models.workflow_result import WorkflowResult


def _append(lines: list[str], *items: str) -> None:
    lines.extend(items)


def _append_kv(lines: list[str], label: str, value: object) -> None:
    lines.append(f"- {label}: {value}")


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
                f"{issue.issue_type} | severity={issue.severity} | evidence={evidence}"
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


def build_mapping_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Standard Mapping Recommendations", ""]
    if result.mapping_summary:
        lines.append(f"- Summary: {result.mapping_summary}")
    if result.mapping_results:
        for mapping_result in result.mapping_results:
            lines.append(
                f"- `{mapping_result.table_name}.{mapping_result.field_name}` -> "
                f"`{mapping_result.recommended_standard_code}` | score={mapping_result.match_score} | "
                f"reason={mapping_result.match_reason}"
            )
    else:
        lines.append("- No standard mapping recommendations generated.")

    lines.extend(["", "# Unmapped or Low-Confidence Fields", ""])
    if result.unmapped_fields:
        for unmapped_field in result.unmapped_fields:
            lines.append(
                f"- `{unmapped_field.table_name}.{unmapped_field.field_name}` | "
                f"best_candidate={unmapped_field.best_candidate_code or 'N/A'} | "
                f"score={unmapped_field.best_candidate_score} | reason={unmapped_field.reason}"
            )
    else:
        lines.append("- No unmapped or low-confidence fields.")

    lines.extend(["", "# Confirmed Mapping Results", ""])
    if result.confirmed_mapping_results:
        for mapping_result in result.confirmed_mapping_results:
            lines.append(
                f"- `{mapping_result.table_name}.{mapping_result.field_name}` -> "
                f"`{mapping_result.recommended_standard_code or 'REJECTED'}` | "
                f"source={mapping_result.confirmed_source or 'review'} | "
                f"action={mapping_result.review_action or 'applied'} | "
                f"note={mapping_result.reviewer_note or 'N/A'}"
            )
    else:
        lines.append("- No confirmed mapping results available.")
    return lines


def build_stg_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# STG Structure Suggestions", ""]
    if result.stg_summary:
        lines.append(f"- Summary: {result.stg_summary}")
    if result.stg_suggestions:
        for table_suggestion in result.stg_suggestions:
            lines.append(
                f"- `{table_suggestion.source_table_name}` -> "
                f"`{table_suggestion.recommended_stg_table_name}` | "
                f"issue_flags={', '.join(table_suggestion.issue_flags) or 'none'}"
            )
        lines.append("")
        lines.append("## STG Field Suggestions")
        lines.append("")
        for field_suggestion in result.stg_field_suggestions:
            lines.append(
                f"- `{field_suggestion.source_table_name}.{field_suggestion.source_field_name}` -> "
                f"`{field_suggestion.recommended_stg_field_name}` | "
                f"type={field_suggestion.recommended_data_type} | "
                f"source={field_suggestion.mapping_source} | action={field_suggestion.action} | "
                f"notes={field_suggestion.notes or 'N/A'}"
            )
    else:
        lines.append("- No STG structure suggestions generated.")

    lines.extend(["", "# Confirmed STG Suggestions", ""])
    if result.confirmed_stg_suggestions:
        for suggestion in result.confirmed_stg_suggestions:
            lines.append(
                f"- `{suggestion.source_table_name}.{suggestion.source_field_name}` -> "
                f"`{suggestion.recommended_stg_field_name}` | "
                f"type={suggestion.recommended_data_type} | "
                f"source={suggestion.confirmed_source or 'review'} | "
                f"action={suggestion.review_action or suggestion.action} | "
                f"note={suggestion.reviewer_note or 'N/A'}"
            )
    else:
        lines.append("- No confirmed STG suggestions available.")
    return lines


def build_quality_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Quality Rule Recommendations", ""]
    if result.quality_rule_summary:
        lines.append(f"- Summary: {result.quality_rule_summary}")
    if result.quality_rule_suggestions:
        for rule in result.quality_rule_suggestions:
            lines.append(
                f"- `{rule.source_table_name}.{rule.source_field_name}` -> "
                f"{rule.rule_type} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"source={rule.recommendation_source} | "
                f"basis={rule.match_basis or 'N/A'} | "
                f"reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No quality rule recommendations generated.")

    lines.extend(["", "# Cross-Field Quality Rules", ""])
    if result.cross_field_quality_rules:
        for rule in result.cross_field_quality_rules:
            lines.append(
                f"- `{rule.source_table_name}` | fields={', '.join(rule.field_group)} | "
                f"{rule.rule_type} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"expression={rule.rule_expression} | reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No cross-field quality rules generated.")

    lines.extend(["", "# Quality Review Queue Summary", ""])
    if result.quality_review_queue_summary:
        for key, value in result.quality_review_queue_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No quality review queue summary available.")

    lines.extend(["", "# Confirmed Quality Rules", ""])
    if result.confirmed_quality_rules:
        for rule in result.confirmed_quality_rules:
            lines.append(
                f"- `{rule.source_table_name}.{rule.source_field_name}` -> "
                f"{rule.rule_type} | scope={rule.rule_scope} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"source={rule.confirmation_source} | "
                f"expression={rule.rule_expression or 'N/A'} | "
                f"reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No confirmed quality rules available.")

    lines.extend(["", "# Quality Rule Review Summary", ""])
    if result.quality_rule_review_summary:
        for key, value in result.quality_rule_review_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No quality rule review summary available.")

    lines.extend(["", "# Rule Export Results", ""])
    if result.rule_export_results:
        for export_result in result.rule_export_results:
            lines.append(
                f"- {export_result.export_format} | status={export_result.status} | "
                f"rules={export_result.rule_count} | path=`{export_result.output_path}`"
            )
    else:
        lines.append("- No rule export results available.")
    return lines


def build_execution_package_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Execution-Ready Governance Package", ""]
    if result.execution_ready_package is not None:
        package = result.execution_ready_package
        lines.append(f"- Package ID: `{package.package_id}`")
        lines.append(f"- Package name: `{package.package_name}`")
        lines.append(f"- Rule count: {package.rule_count}")
        if result.execution_package_summary:
            lines.append(
                f"- Field rules: {result.execution_package_summary.get('field_rule_count', 'N/A')}"
            )
            lines.append(
                f"- Cross-field rules: {result.execution_package_summary.get('cross_field_rule_count', 'N/A')}"
            )
            lines.append(
                f"- Non-native rules: {result.execution_package_summary.get('non_native_rule_count', 'N/A')}"
            )
        lines.append(f"- Source profile: {package.source_profile or 'N/A'}")
        lines.append(f"- Summary: {package.summary or 'N/A'}")
        if package.rules:
            lines.append("")
            lines.append("## Execution-Ready Rules")
            lines.append("")
            for rule in package.rules:
                lines.append(
                    f"- `{rule.rule_id}` | `{rule.source_table_name}.{rule.source_field_name}` | "
                    f"{rule.rule_type} | scope={rule.rule_scope} | semantic={rule.semantic_type or 'N/A'} | "
                    f"mode={rule.execution_mode or 'N/A'} | priority={rule.priority or 'N/A'}"
                )
    else:
        lines.append("- No execution-ready package available.")

    lines.extend(["", "# Execution Package Export Results", ""])
    if result.execution_package_export_results:
        for export_result in result.execution_package_export_results:
            lines.append(
                f"- {export_result.export_format} | status={export_result.status} | "
                f"package=`{export_result.package_id}` | rules={export_result.rule_count} | "
                f"path=`{export_result.output_path}`"
            )
    else:
        lines.append("- No execution package export results available.")
    return lines


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


def build_delivery_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Governance Delivery Package", ""]
    if result.confirmation_workbook_results:
        lines.append(
            f"- Confirmation workbook count: {len(result.confirmation_workbook_results)}"
        )
        for workbook in result.confirmation_workbook_results:
            lines.append(
                f"- {workbook.workbook_type} | rows={workbook.row_count} | path=`{workbook.output_path}`"
            )
    else:
        lines.append("- No confirmation workbooks available.")
    if result.governance_delivery_package_result is not None:
        package_result = result.governance_delivery_package_result
        lines.append(f"- Delivery package: `{package_result.package_name}`")
        lines.append(f"- Output dir: `{package_result.output_dir}`")
        lines.append(f"- Generated files: {len(package_result.generated_files)}")
    if result.governance_delivery_manifest is not None:
        manifest = result.governance_delivery_manifest
        lines.append(
            f"- Manifest artifacts: {len(manifest.included_artifacts)} | generated_at={manifest.generated_at or 'N/A'}"
        )
    return lines


def build_batch_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Batch Processing Summary", ""]
    if result.batch_group_results:
        lines.append(f"- Batch groups: {len(result.batch_group_results)}")
        for group in result.batch_group_results:
            lines.append(
                f"- `{group.group_name}` | files={group.file_count} | tables={group.table_count} | status={group.status}"
            )
    else:
        lines.append("- No batch group results available.")

    lines.extend(["", "# Incremental Diff Summary", ""])
    if result.incremental_diff_summary is not None:
        summary = result.incremental_diff_summary
        lines.append(f"- Total objects: {summary.total_objects}")
        lines.append(f"- New: {summary.new_count}")
        lines.append(f"- Changed: {summary.changed_count}")
        lines.append(f"- Unchanged: {summary.unchanged_count}")
        lines.append(f"- Removed: {summary.removed_count}")
        lines.append(f"- Pending review: {summary.pending_review_count}")
        lines.append(f"- Summary: {summary.summary or 'N/A'}")
    else:
        lines.append("- No incremental diff summary available.")

    lines.extend(["", "# Rerun Scope Summary", ""])
    if result.rerun_scope_summary:
        for key, value in result.rerun_scope_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No rerun scope summary available.")
    return lines


def build_workbook_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Workbook Import Summary", ""]
    if result.workbook_import_summaries:
        for summary in result.workbook_import_summaries:
            lines.append(
                f"- {summary.workbook_type} | imported={summary.imported_count} | "
                f"skipped={summary.skipped_count} | invalid={summary.invalid_count}"
            )
    else:
        lines.append("- No workbook import summaries available.")

    lines.extend(["", "# Confirmation Round-Trip Results", ""])
    if result.roundtrip_results:
        for roundtrip in result.roundtrip_results:
            lines.append(
                f"- {roundtrip.workbook_type} | status={roundtrip.status} | "
                f"review_records={roundtrip.generated_review_records_count} | "
                f"backlog_updates={roundtrip.generated_backlog_updates_count} | "
                f"changed_objects={len(roundtrip.changed_object_keys)}"
            )
        if result.roundtrip_changed_objects_summary:
            lines.append(
                f"- Changed object count: {result.roundtrip_changed_objects_summary.get('changed_object_count', 0)}"
            )
    else:
        lines.append("- No confirmation round-trip results available.")
    return lines


def build_template_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Domain Governance Pack", ""]
    if result.domain_pack_match:
        lines.append(
            f"- Matched pack: `{result.domain_pack_match.matched_pack_name or 'N/A'}`"
        )
        lines.append(f"- Confidence: {result.domain_pack_match.confidence}")
        lines.append(f"- Fallback used: {result.domain_pack_match.fallback_used}")
        lines.append(f"- Matched tokens: {result.domain_pack_match.matched_tokens}")
    else:
        lines.append("- No domain governance pack match attached.")

    lines.extend(["", "# Project Template Applied", ""])
    if result.project_template_result:
        template = result.project_template_result
        lines.append(f"- Template: `{template.template_name}`")
        lines.append(f"- Domain pack: `{template.selected_domain_pack or 'N/A'}`")
        lines.append(f"- Workflow profile: `{template.workflow_profile or 'N/A'}`")
        lines.append(f"- Status: {template.status}")
    else:
        lines.append("- No project template result attached.")

    lines.extend(["", "# Intake Template Diagnosis", ""])
    if result.intake_match_result:
        intake_match = result.intake_match_result
        lines.append(f"- Matched profile: `{intake_match.matched_profile_name or 'N/A'}`")
        lines.append(f"- Confidence: {intake_match.confidence}")
        lines.append(f"- Matched sheet: `{intake_match.matched_sheet_name or 'N/A'}`")
        lines.append(f"- Missing required fields: {intake_match.missing_required_fields}")
    else:
        lines.append("- No intake template diagnosis attached.")

    lines.extend(["", "# Input Normalization Summary", ""])
    if result.intake_normalization_result:
        normalization = result.intake_normalization_result
        lines.append(f"- Profile: `{normalization.profile_name}`")
        lines.append(f"- Rows: {normalization.row_count}")
        lines.append(f"- Tables: {normalization.table_count}")
        lines.append(f"- Status: {normalization.status}")
        if result.intake_mapping_result:
            lines.append(
                f"- Unmapped source columns: {len(result.intake_mapping_result.unmapped_source_columns)}"
            )
    else:
        lines.append("- No intake normalization summary attached.")

    lines.extend(["", "# Confirmation Template Diagnosis", ""])
    if result.confirmation_template_match_result:
        template_match = result.confirmation_template_match_result
        lines.append(
            f"- Matched template: `{template_match.matched_template_name or 'N/A'}`"
        )
        lines.append(f"- Workbook type: `{template_match.workbook_type or 'N/A'}`")
        lines.append(f"- Confidence: {template_match.confidence}")
        lines.append(f"- Matched sheet: `{template_match.matched_sheet_name or 'N/A'}`")
        lines.append(f"- Missing required fields: {template_match.missing_required_fields}")
    else:
        lines.append("- No confirmation template diagnosis attached.")

    lines.extend(["", "# Confirmation Template Mapping Summary", ""])
    if result.confirmation_template_mapping_result:
        template_mapping = result.confirmation_template_mapping_result
        lines.append(f"- Template: `{template_mapping.template_name}`")
        lines.append(f"- Status: {template_mapping.status}")
        lines.append(f"- Mapped fields: {sorted(template_mapping.mapped_fields.keys())}")
        lines.append(
            f"- Unmapped source columns: {template_mapping.unmapped_source_columns}"
        )
    else:
        lines.append("- No confirmation template mapping summary attached.")
    return lines


def build_review_section(result: WorkflowResult) -> list[str]:
    lines = ["", "# Review Summary", ""]
    if result.review_summary:
        lines.append(f"- Accepted: {result.review_summary.accepted_count}")
        lines.append(f"- Rejected: {result.review_summary.rejected_count}")
        lines.append(f"- Edited: {result.review_summary.edited_count}")
        lines.append(f"- Manual Review: {result.review_summary.manual_review_count}")
        lines.append(f"- Total Reviewed: {result.review_summary.total_reviewed_count}")
    else:
        lines.append("- No review summary available.")
    return lines

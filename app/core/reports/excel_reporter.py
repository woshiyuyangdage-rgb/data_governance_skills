"""Excel report export helpers."""

from pathlib import Path

import pandas as pd

from app.core.models.workflow_result import WorkflowResult
from app.core.utils.file_utils import ensure_directory
from app.core.utils.result_utils import (
    backlog_sla_statuses_to_dataframe,
    backlog_summary_to_dataframe,
    confirmed_quality_rules_to_dataframe,
    cross_field_quality_rules_to_dataframe,
    execution_package_export_results_to_dataframe,
    execution_package_summary_to_dataframe,
    execution_ready_rules_to_dataframe,
    governance_backlog_items_to_dataframe,
    governance_gaps_to_dataframe,
    governance_portfolio_summary_to_dataframe,
    governance_work_package_summary_to_dataframe,
    issues_to_dataframe,
    mapping_results_to_dataframe,
    progress_snapshot_to_dataframe,
    quality_rules_to_dataframe,
    quality_review_queue_summary_to_dataframe,
    quality_rule_review_summary_to_dataframe,
    readiness_scores_to_dataframe,
    remediation_actions_to_dataframe,
    review_summary_to_dataframe,
    rule_export_results_to_dataframe,
    skill_outputs_to_dataframe,
    stg_fields_to_dataframe,
    stg_tables_to_dataframe,
    tasks_to_dataframe,
    unmapped_fields_to_dataframe,
)


def export_workflow_result_to_excel(
    result: WorkflowResult,
    output_path: str,
) -> str:
    """Export a workflow result to a multi-sheet Excel workbook."""
    path = Path(output_path)
    ensure_directory(path.parent)

    summary_df = pd.DataFrame(
        [
            {
                "status": result.status,
                "message": result.message,
                "input_table_count": result.input_table_count,
                "issue_count": result.issue_count,
                "task_count": result.task_count,
                "mapping_result_count": len(result.mapping_results),
                "confirmed_mapping_result_count": len(result.confirmed_mapping_results),
                "unmapped_field_count": len(result.unmapped_fields),
                "stg_table_count": len(result.stg_suggestions),
                "stg_field_count": len(result.stg_field_suggestions),
                "confirmed_stg_field_count": len(result.confirmed_stg_suggestions),
                "quality_rule_count": len(result.quality_rule_suggestions),
                "cross_field_quality_rule_count": len(result.cross_field_quality_rules),
                "quality_rule_package_count": len(result.quality_rule_packages),
                "confirmed_quality_rule_count": len(result.confirmed_quality_rules),
                "rule_export_result_count": len(result.rule_export_results),
                "execution_ready_rule_count": (
                    result.execution_ready_package.rule_count
                    if result.execution_ready_package is not None
                    else 0
                ),
                "execution_package_export_result_count": len(
                    result.execution_package_export_results
                ),
                "readiness_score_count": len(result.readiness_scores),
                "governance_gap_count": len(result.governance_gaps),
                "remediation_action_count": len(result.remediation_actions),
                "governance_backlog_item_count": len(result.governance_backlog_items),
                "backlog_sla_status_count": len(result.backlog_sla_statuses),
                "portfolio_overdue_count": (
                    result.governance_portfolio_summary.overdue_count
                    if result.governance_portfolio_summary is not None
                    else 0
                ),
                "confirmation_workbook_count": len(
                    result.confirmation_workbook_results
                ),
                "delivery_generated_file_count": (
                    len(result.governance_delivery_package_result.generated_files)
                    if result.governance_delivery_package_result is not None
                    else 0
                ),
                "batch_group_count": len(result.batch_group_results),
                "incremental_diff_item_count": len(result.incremental_diff_items),
                "rerun_object_count": result.rerun_scope_summary.get(
                    "rerun_object_count",
                    0,
                ),
                "workbook_import_summary_count": len(result.workbook_import_summaries),
                "roundtrip_result_count": len(result.roundtrip_results),
                "domain_pack_name": (
                    result.project_template_result.selected_domain_pack
                    if result.project_template_result is not None
                    else None
                ),
                "project_template_name": (
                    result.project_template_result.template_name
                    if result.project_template_result is not None
                    else None
                ),
                "intake_profile_name": (
                    result.intake_normalization_result.profile_name
                    if result.intake_normalization_result is not None
                    else None
                ),
                "intake_row_count": (
                    result.intake_normalization_result.row_count
                    if result.intake_normalization_result is not None
                    else 0
                ),
                "confirmation_template_name": (
                    result.confirmation_template_mapping_result.template_name
                    if result.confirmation_template_mapping_result is not None
                    else None
                ),
            }
        ]
    )
    issues_df = issues_to_dataframe(result.issues)
    tasks_df = tasks_to_dataframe(result.tasks)
    skill_outputs_df = skill_outputs_to_dataframe(result.skill_outputs)
    mapping_results_df = mapping_results_to_dataframe(result.mapping_results)
    confirmed_mapping_results_df = mapping_results_to_dataframe(
        result.confirmed_mapping_results
    )
    unmapped_fields_df = unmapped_fields_to_dataframe(result.unmapped_fields)
    stg_tables_df = stg_tables_to_dataframe(result.stg_suggestions)
    stg_fields_df = stg_fields_to_dataframe(result.stg_field_suggestions)
    confirmed_stg_fields_df = stg_fields_to_dataframe(result.confirmed_stg_suggestions)
    quality_rules_df = quality_rules_to_dataframe(result.quality_rule_suggestions)
    cross_field_quality_rules_df = cross_field_quality_rules_to_dataframe(
        result.cross_field_quality_rules
    )
    confirmed_quality_rules_df = confirmed_quality_rules_to_dataframe(
        result.confirmed_quality_rules
    )
    quality_rule_summary_df = pd.DataFrame(
        [
            {
                "quality_rule_count": len(result.quality_rule_suggestions),
                "quality_rule_package_count": len(result.quality_rule_packages),
                "confirmed_quality_rule_count": len(result.confirmed_quality_rules),
                "quality_rule_summary": result.quality_rule_summary,
            }
        ]
    )
    quality_rule_review_summary_df = quality_rule_review_summary_to_dataframe(
        result.quality_rule_review_summary
    )
    quality_review_queue_summary_df = quality_review_queue_summary_to_dataframe(
        result.quality_review_queue_summary
    )
    rule_export_results_df = rule_export_results_to_dataframe(result.rule_export_results)
    execution_ready_rules_df = execution_ready_rules_to_dataframe(
        result.execution_ready_package
    )
    execution_package_summary_df = execution_package_summary_to_dataframe(
        result.execution_ready_package,
        result.execution_package_summary,
    )
    execution_package_export_results_df = execution_package_export_results_to_dataframe(
        result.execution_package_export_results
    )
    readiness_scores_df = readiness_scores_to_dataframe(result.readiness_scores)
    governance_gaps_df = governance_gaps_to_dataframe(result.governance_gaps)
    remediation_actions_df = remediation_actions_to_dataframe(
        result.remediation_actions
    )
    governance_work_package_summary_df = governance_work_package_summary_to_dataframe(
        result.governance_work_package,
        result.readiness_summary,
    )
    governance_backlog_items_df = governance_backlog_items_to_dataframe(
        result.governance_backlog_items
    )
    backlog_summary_df = backlog_summary_to_dataframe(result.backlog_summary)
    backlog_sla_statuses_df = backlog_sla_statuses_to_dataframe(
        result.backlog_sla_statuses
    )
    governance_portfolio_summary_df = governance_portfolio_summary_to_dataframe(
        result.governance_portfolio_summary
    )
    progress_snapshot_df = progress_snapshot_to_dataframe(result.progress_snapshot)
    confirmation_workbook_results_df = pd.DataFrame(
        [
            workbook.model_dump()
            for workbook in result.confirmation_workbook_results
        ]
    )
    governance_delivery_manifest_df = pd.DataFrame(
        result.governance_delivery_manifest.included_artifacts
        if result.governance_delivery_manifest is not None
        else []
    )
    governance_delivery_package_df = pd.DataFrame(
        [
            {
                "package_name": result.governance_delivery_package_result.package_name,
                "output_dir": result.governance_delivery_package_result.output_dir,
                "status": result.governance_delivery_package_result.status,
                "message": result.governance_delivery_package_result.message,
                "generated_file_count": len(
                    result.governance_delivery_package_result.generated_files
                ),
            }
        ]
        if result.governance_delivery_package_result is not None
        else []
    )
    batch_group_results_df = pd.DataFrame(
        [group.model_dump() for group in result.batch_group_results]
    )
    incremental_diff_items_df = pd.DataFrame(
        [item.model_dump() for item in result.incremental_diff_items]
    )
    incremental_diff_summary_df = pd.DataFrame(
        [result.incremental_diff_summary.model_dump()]
        if result.incremental_diff_summary is not None
        else []
    )
    rerun_scope_summary_df = pd.DataFrame(
        [
            {"metric": key, "value": value}
            for key, value in result.rerun_scope_summary.items()
        ]
    )
    workbook_import_summary_df = pd.DataFrame(
        [summary.model_dump() for summary in result.workbook_import_summaries]
    )
    roundtrip_results_df = pd.DataFrame(
        [roundtrip.model_dump() for roundtrip in result.roundtrip_results]
    )
    domain_pack_match_df = pd.DataFrame(
        [result.domain_pack_match.model_dump()] if result.domain_pack_match is not None else []
    )
    project_template_df = pd.DataFrame(
        [result.project_template_result.model_dump()]
        if result.project_template_result is not None
        else []
    )
    intake_match_df = pd.DataFrame(
        [result.intake_match_result.model_dump()]
        if result.intake_match_result is not None
        else []
    )
    intake_mapping_df = pd.DataFrame(
        [result.intake_mapping_result.model_dump()]
        if result.intake_mapping_result is not None
        else []
    )
    intake_normalization_df = pd.DataFrame(
        [result.intake_normalization_result.model_dump()]
        if result.intake_normalization_result is not None
        else []
    )
    confirmation_template_match_df = pd.DataFrame(
        [result.confirmation_template_match_result.model_dump()]
        if result.confirmation_template_match_result is not None
        else []
    )
    confirmation_template_mapping_df = pd.DataFrame(
        [result.confirmation_template_mapping_result.model_dump()]
        if result.confirmation_template_mapping_result is not None
        else []
    )
    review_summary_df = review_summary_to_dataframe(result.review_summary)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="summary", index=False)
        issues_df.to_excel(writer, sheet_name="issues", index=False)
        tasks_df.to_excel(writer, sheet_name="tasks", index=False)
        skill_outputs_df.to_excel(writer, sheet_name="skill_outputs_overview", index=False)
        mapping_results_df.to_excel(writer, sheet_name="standard_mapping", index=False)
        confirmed_mapping_results_df.to_excel(
            writer,
            sheet_name="confirmed_standard_mapping",
            index=False,
        )
        unmapped_fields_df.to_excel(writer, sheet_name="unmapped_fields", index=False)
        stg_tables_df.to_excel(writer, sheet_name="stg_tables", index=False)
        stg_fields_df.to_excel(writer, sheet_name="stg_fields", index=False)
        confirmed_stg_fields_df.to_excel(
            writer,
            sheet_name="confirmed_stg_fields",
            index=False,
        )
        quality_rules_df.to_excel(writer, sheet_name="quality_rules", index=False)
        cross_field_quality_rules_df.to_excel(
            writer,
            sheet_name="cross_field_quality_rules",
            index=False,
        )
        confirmed_quality_rules_df.to_excel(
            writer,
            sheet_name="confirmed_quality_rules",
            index=False,
        )
        quality_rule_summary_df.to_excel(
            writer,
            sheet_name="quality_rule_summary",
            index=False,
        )
        quality_rule_review_summary_df.to_excel(
            writer,
            sheet_name="quality_rule_review_summary",
            index=False,
        )
        quality_review_queue_summary_df.to_excel(
            writer,
            sheet_name="quality_review_queue_summary",
            index=False,
        )
        rule_export_results_df.to_excel(
            writer,
            sheet_name="rule_export_results",
            index=False,
        )
        execution_ready_rules_df.to_excel(
            writer,
            sheet_name="execution_ready_rules",
            index=False,
        )
        execution_package_summary_df.to_excel(
            writer,
            sheet_name="execution_package_summary",
            index=False,
        )
        execution_package_export_results_df.to_excel(
            writer,
            sheet_name="execution_package_export_results",
            index=False,
        )
        readiness_scores_df.to_excel(
            writer,
            sheet_name="readiness_scores",
            index=False,
        )
        governance_gaps_df.to_excel(
            writer,
            sheet_name="governance_gaps",
            index=False,
        )
        remediation_actions_df.to_excel(
            writer,
            sheet_name="remediation_actions",
            index=False,
        )
        governance_work_package_summary_df.to_excel(
            writer,
            sheet_name="governance_work_package_summary",
            index=False,
        )
        governance_backlog_items_df.to_excel(
            writer,
            sheet_name="governance_backlog_items",
            index=False,
        )
        backlog_summary_df.to_excel(
            writer,
            sheet_name="backlog_summary",
            index=False,
        )
        backlog_sla_statuses_df.to_excel(
            writer,
            sheet_name="backlog_sla_statuses",
            index=False,
        )
        governance_portfolio_summary_df.to_excel(
            writer,
            sheet_name="governance_portfolio_summary",
            index=False,
        )
        progress_snapshot_df.to_excel(
            writer,
            sheet_name="progress_snapshot",
            index=False,
        )
        confirmation_workbook_results_df.to_excel(
            writer,
            sheet_name="confirmation_workbooks",
            index=False,
        )
        governance_delivery_manifest_df.to_excel(
            writer,
            sheet_name="delivery_manifest",
            index=False,
        )
        governance_delivery_package_df.to_excel(
            writer,
            sheet_name="delivery_package",
            index=False,
        )
        batch_group_results_df.to_excel(
            writer,
            sheet_name="batch_group_results",
            index=False,
        )
        incremental_diff_items_df.to_excel(
            writer,
            sheet_name="incremental_diff_items",
            index=False,
        )
        incremental_diff_summary_df.to_excel(
            writer,
            sheet_name="incremental_diff_summary",
            index=False,
        )
        rerun_scope_summary_df.to_excel(
            writer,
            sheet_name="rerun_scope_summary",
            index=False,
        )
        workbook_import_summary_df.to_excel(
            writer,
            sheet_name="workbook_import_summary",
            index=False,
        )
        roundtrip_results_df.to_excel(
            writer,
            sheet_name="roundtrip_results",
            index=False,
        )
        domain_pack_match_df.to_excel(
            writer,
            sheet_name="domain_pack_match",
            index=False,
        )
        project_template_df.to_excel(
            writer,
            sheet_name="project_template",
            index=False,
        )
        intake_match_df.to_excel(writer, sheet_name="intake_match", index=False)
        intake_mapping_df.to_excel(writer, sheet_name="intake_mapping", index=False)
        intake_normalization_df.to_excel(
            writer,
            sheet_name="intake_normalization",
            index=False,
        )
        confirmation_template_match_df.to_excel(
            writer,
            sheet_name="confirmation_template_match",
            index=False,
        )
        confirmation_template_mapping_df.to_excel(
            writer,
            sheet_name="confirmation_tpl_mapping",
            index=False,
        )
        review_summary_df.to_excel(writer, sheet_name="review_summary", index=False)

    return str(path)


def export_excel_report(report_data: WorkflowResult, output_path: str) -> str:
    """Backward-compatible alias for Excel workflow export."""
    return export_workflow_result_to_excel(report_data, output_path)

"""JSON report export helpers."""

import json
from pathlib import Path
from typing import Any

from app.core.models.workflow_result import WorkflowResult
from app.core.utils.file_utils import ensure_directory


def _serialize(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def export_workflow_result_to_json(
    result: WorkflowResult,
    output_path: str,
) -> str:
    """Export a workflow result to a structured JSON file."""
    path = Path(output_path)
    ensure_directory(path.parent)

    payload = {
        "status": result.status,
        "message": result.message,
        "input_table_count": result.input_table_count,
        "issue_count": result.issue_count,
        "task_count": result.task_count,
        "issues": _serialize(result.issues),
        "tasks": _serialize(result.tasks),
        "field_description_suggestions": _serialize(
            result.field_description_suggestions
        ),
        "table_semantic_summaries": _serialize(result.table_semantic_summaries),
        "semantic_enrichment_summary": result.semantic_enrichment_summary,
        "mapping_results": _serialize(result.mapping_results),
        "confirmed_mapping_results": _serialize(result.confirmed_mapping_results),
        "unmapped_fields": _serialize(result.unmapped_fields),
        "mapping_summary": result.mapping_summary,
        "stg_suggestions": _serialize(result.stg_suggestions),
        "stg_field_suggestions": _serialize(result.stg_field_suggestions),
        "confirmed_stg_suggestions": _serialize(result.confirmed_stg_suggestions),
        "stg_summary": result.stg_summary,
        "quality_rule_suggestions": _serialize(result.quality_rule_suggestions),
        "cross_field_quality_rules": _serialize(result.cross_field_quality_rules),
        "quality_rule_packages": _serialize(result.quality_rule_packages),
        "quality_rule_summary": result.quality_rule_summary,
        "confirmed_quality_rules": _serialize(result.confirmed_quality_rules),
        "quality_rule_review_summary": _serialize(result.quality_rule_review_summary),
        "quality_review_queue_summary": _serialize(result.quality_review_queue_summary),
        "rule_export_results": _serialize(result.rule_export_results),
        "execution_ready_package": _serialize(result.execution_ready_package),
        "execution_package_summary": _serialize(result.execution_package_summary),
        "execution_package_export_results": _serialize(
            result.execution_package_export_results
        ),
        "readiness_scores": _serialize(result.readiness_scores),
        "ai_ready_scores": _serialize(result.ai_ready_scores),
        "ai_ready_summary": _serialize(result.ai_ready_summary),
        "governance_gaps": _serialize(result.governance_gaps),
        "remediation_actions": _serialize(result.remediation_actions),
        "governance_work_package": _serialize(result.governance_work_package),
        "readiness_summary": _serialize(result.readiness_summary),
        "governance_backlog_items": _serialize(result.governance_backlog_items),
        "backlog_summary": _serialize(result.backlog_summary),
        "backlog_sla_statuses": _serialize(result.backlog_sla_statuses),
        "governance_portfolio_summary": _serialize(result.governance_portfolio_summary),
        "progress_snapshot": _serialize(result.progress_snapshot),
        "confirmation_workbook_results": _serialize(
            result.confirmation_workbook_results
        ),
        "governance_delivery_manifest": _serialize(
            result.governance_delivery_manifest
        ),
        "governance_delivery_package_result": _serialize(
            result.governance_delivery_package_result
        ),
        "batch_run_result": _serialize(result.batch_run_result),
        "batch_group_results": _serialize(result.batch_group_results),
        "incremental_diff_items": _serialize(result.incremental_diff_items),
        "incremental_diff_summary": _serialize(result.incremental_diff_summary),
        "rerun_scope_summary": _serialize(result.rerun_scope_summary),
        "workbook_import_summaries": _serialize(result.workbook_import_summaries),
        "roundtrip_results": _serialize(result.roundtrip_results),
        "roundtrip_changed_objects_summary": _serialize(
            result.roundtrip_changed_objects_summary
        ),
        "domain_pack_match": _serialize(result.domain_pack_match),
        "project_template_result": _serialize(result.project_template_result),
        "intake_match_result": _serialize(result.intake_match_result),
        "intake_mapping_result": _serialize(result.intake_mapping_result),
        "intake_normalization_result": _serialize(result.intake_normalization_result),
        "confirmation_template_match_result": _serialize(
            result.confirmation_template_match_result
        ),
        "confirmation_template_mapping_result": _serialize(
            result.confirmation_template_mapping_result
        ),
        "review_summary": _serialize(result.review_summary),
        "skill_outputs": _serialize(result.skill_outputs),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def export_json_report(report_data: WorkflowResult, output_path: str) -> str:
    """Backward-compatible alias for JSON workflow export."""
    return export_workflow_result_to_json(report_data, output_path)

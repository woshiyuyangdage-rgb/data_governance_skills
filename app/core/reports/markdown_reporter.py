"""Markdown report export helpers."""

from pathlib import Path

from app.core.models.workflow_result import WorkflowResult
from app.core.reports.markdown_reporter_sections import (
    build_batch_sections,
    build_delivery_sections,
    build_diagnosis_issues_section,
    build_execution_package_sections,
    build_governance_sections,
    build_governance_tasks_section,
    build_mapping_sections,
    build_project_summary,
    build_quality_sections,
    build_review_section,
    build_semantic_enrichment_sections,
    build_stg_sections,
    build_template_sections,
    build_workbook_sections,
)
from app.core.utils.file_utils import ensure_directory


def export_workflow_result_to_markdown(
    result: WorkflowResult,
    output_path: str,
) -> str:
    """Export a workflow result to a readable Markdown report."""
    path = Path(output_path)
    ensure_directory(path.parent)

    lines = build_project_summary(result)
    lines.extend(build_diagnosis_issues_section(result))
    lines.extend(build_governance_tasks_section(result))
    lines.extend(build_semantic_enrichment_sections(result))
    lines.extend(build_mapping_sections(result))
    lines.extend(build_stg_sections(result))
    lines.extend(build_quality_sections(result))
    lines.extend(build_execution_package_sections(result))
    lines.extend(build_governance_sections(result))
    lines.extend(build_delivery_sections(result))
    lines.extend(build_batch_sections(result))
    lines.extend(build_workbook_sections(result))
    lines.extend(build_template_sections(result))
    lines.extend(build_review_section(result))

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def export_markdown_report(report_data: WorkflowResult, output_path: str) -> str:
    """Backward-compatible alias for Markdown workflow export."""
    return export_workflow_result_to_markdown(report_data, output_path)

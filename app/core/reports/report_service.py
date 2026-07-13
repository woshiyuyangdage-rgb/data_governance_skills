"""Unified report export service."""

from datetime import datetime
from pathlib import Path

from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.profile_loader import get_workflow_profile
from app.core.reports.excel_reporter import export_workflow_result_to_excel
from app.core.reports.json_reporter import export_workflow_result_to_json
from app.core.reports.markdown_reporter import export_workflow_result_to_markdown
from app.core.utils.file_utils import (
    ensure_directory,
    resolve_allowed_local_path,
    sanitize_filename,
)

DEFAULT_REPORT_OUTPUT_DIR = Path(__file__).resolve().parents[3] / "outputs" / "reports"

REPORT_MODE_PREFIX_MAP = {
    "diagnosis": "diagnosis",
    "mapping": "mapping",
    "stg": "stg",
    "quality": "quality",
    "confirmed": "confirmed",
    "package": "package",
    "readiness": "readiness",
    "remediation": "remediation",
    "backlog": "backlog",
    "portfolio": "portfolio",
    "batch": "batch",
    "incremental": "incremental",
    "delivery": "delivery",
    "workbook": "workbook",
    "import": "import",
    "rerun": "rerun",
}


def build_report_base_filename(
    profile_name: str,
    base_filename: str | None = None,
    timestamp: str | None = None,
) -> str:
    """Build a safe report base filename from a workflow profile."""
    if base_filename:
        return sanitize_filename(base_filename)

    profile = get_workflow_profile(profile_name)
    report_mode = str(profile.default_report_mode or "workflow").strip().lower()
    prefix = REPORT_MODE_PREFIX_MAP.get(report_mode, "workflow")
    resolved_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    return sanitize_filename(f"{prefix}_{resolved_timestamp}")


def export_all_reports(
    result: WorkflowResult,
    output_dir: str,
    base_filename: str,
) -> dict[str, str]:
    """Export JSON, Markdown, and Excel reports in one call."""
    resolved_output_dir = resolve_allowed_local_path(
        output_dir,
        path_label="output_dir",
    )
    ensure_directory(resolved_output_dir)
    safe_name = sanitize_filename(base_filename)

    json_path = export_workflow_result_to_json(
        result,
        str(resolved_output_dir / f"{safe_name}.json"),
    )
    markdown_path = export_workflow_result_to_markdown(
        result,
        str(resolved_output_dir / f"{safe_name}.md"),
    )
    excel_path = export_workflow_result_to_excel(
        result,
        str(resolved_output_dir / f"{safe_name}.xlsx"),
    )

    return {
        "json": json_path,
        "markdown": markdown_path,
        "excel": excel_path,
    }

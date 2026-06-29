"""Report export interfaces."""

from app.core.reports.excel_reporter import (
    export_excel_report,
    export_workflow_result_to_excel,
)
from app.core.reports.json_reporter import (
    export_json_report,
    export_workflow_result_to_json,
)
from app.core.reports.markdown_reporter import (
    export_markdown_report,
    export_workflow_result_to_markdown,
)


def export_all_reports(*args, **kwargs):
    """Lazily export all reports without triggering router/report import cycles."""
    from app.core.reports.report_service import (
        export_all_reports as _export_all_reports,
    )

    return _export_all_reports(*args, **kwargs)

__all__ = [
    "export_excel_report",
    "export_markdown_report",
    "export_json_report",
    "export_workflow_result_to_excel",
    "export_workflow_result_to_markdown",
    "export_workflow_result_to_json",
    "export_all_reports",
]

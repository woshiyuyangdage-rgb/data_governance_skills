"""Reports page for viewing and exporting workflow outputs."""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.page_utils import (
    REPORT_OUTPUT_DIR,
    ensure_agent_shell_session_id,
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_latest_report_paths,
    get_report_export_history,
    get_workflow_result,
    initialize_session_state,
    record_report_paths,
)
from app.ui.result_detail_viewer import render_result_detail_viewer
from app.ui.result_overview import (
    build_result_artifacts,
    render_result_artifacts,
    render_result_overview,
)
from app.ui.status_blocks import render_bullet_list, render_page_header

ensure_project_root_on_path()

from app.core.agent.session_store import set_last_exported_files
from app.core.reports.report_service import export_all_reports

initialize_session_state()

REPORT_MIME_TYPES = {
    "json": "application/json",
    "markdown": "text/markdown",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

render_page_header(
    "报告与结果明细",
    "先在页面查看当前工作流结果明细，再按需导出 JSON、Markdown、Excel 交付文件。",
)

result = get_workflow_result()
if result is None:
    st.warning("当前没有可查看或导出的工作流结果，请先完成诊断。")
else:
    current_file = get_current_input_file_path() or "unknown_input"
    render_result_overview(
        build_workflow_overview(
            result,
            title="结果总览",
            next_step="先展开页面明细核对结果，再按需导出交付文件或回到评审页固化覆盖。",
        )
    )

    st.subheader("页面明细")
    render_result_detail_viewer(result, key_prefix="reports_result_detail")

    export_col1, export_col2 = st.columns([1, 2])
    with export_col1:
        if st.button("导出报告", type="primary", use_container_width=True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{Path(current_file).stem}_{timestamp}"
            try:
                report_paths = export_all_reports(result, str(REPORT_OUTPUT_DIR), base_name)
            except Exception as exc:
                st.error(f"导出失败: {exc}")
            else:
                set_last_exported_files(ensure_agent_shell_session_id(), report_paths)
                record_report_paths(report_paths)
                st.success("报告已导出。")

    with export_col2:
        latest_report_paths = get_latest_report_paths()
        if latest_report_paths:
            render_explanation_block(
                "最近一次导出",
                summary="下面是可下载的本地文件。",
                details=list(latest_report_paths.items()),
            )
            render_result_artifacts(
                build_result_artifacts(
                    latest_report_paths,
                    mime_by_label=REPORT_MIME_TYPES,
                ),
                use_container_width=True,
            )
        else:
            st.info("暂无最近导出文件。")

history = get_report_export_history()
if history:
    st.subheader("导出历史")
    for export_index, export_paths in enumerate(reversed(history), start=1):
        with st.expander(f"导出 {export_index}", expanded=export_index == 1):
            render_bullet_list(
                None,
                [
                    f"`{report_type}`: {report_path}"
                    for report_type, report_path in export_paths.items()
                ],
            )

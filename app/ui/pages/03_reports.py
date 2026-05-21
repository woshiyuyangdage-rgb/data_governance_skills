"""Reports page for exporting workflow outputs."""

from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    REPORT_OUTPUT_DIR,
    ensure_agent_shell_session_id,
    ensure_project_root_on_path,
    initialize_session_state,
)
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview

ensure_project_root_on_path()

from app.core.agent.session_store import set_last_exported_files
from app.core.reports.report_service import export_all_reports

initialize_session_state()

st.title("导出报告")
st.write("把当前工作流结果整理成 JSON、Markdown、Excel 三类交付物。")

result = st.session_state.get("workflow_result")
if result is None:
    st.warning("当前没有可导出的工作流结果，请先完成诊断。")
else:
    current_file = st.session_state.get("workflow_result_file_path") or "unknown_input"
    render_result_overview(
        build_workflow_overview(
            result,
            title="导出总览",
            next_step="导出后可以直接下载，或回到评审页继续固化覆盖。",
        )
    )

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
                st.session_state["latest_report_paths"] = report_paths
                history = list(st.session_state.get("report_export_history", []))
                history.append(report_paths)
                st.session_state["report_export_history"] = history[-10:]
                st.success("报告已导出。")

    with export_col2:
        latest_report_paths = st.session_state.get("latest_report_paths", {})
        if latest_report_paths:
            render_explanation_block(
                "最近一次导出",
                summary="下面是可下载的本地文件。",
                details=list(latest_report_paths.items()),
            )
            for report_type, report_path in latest_report_paths.items():
                path = Path(report_path)
                if path.exists():
                    mime = {
                        "json": "application/json",
                        "markdown": "text/markdown",
                        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    }.get(report_type, "application/octet-stream")
                    st.download_button(
                        label=f"下载 {report_type}",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime=mime,
                        key=f"download_{report_type}_{path.name}",
                        use_container_width=True,
                    )
        else:
            st.info("暂无最近导出文件。")

history = st.session_state.get("report_export_history", [])
if history:
    st.subheader("导出历史")
    for export_index, export_paths in enumerate(reversed(history), start=1):
        with st.expander(f"导出 {export_index}", expanded=export_index == 1):
            for report_type, report_path in export_paths.items():
                st.write(f"- `{report_type}`: {report_path}")

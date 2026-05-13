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

ensure_project_root_on_path()

from app.core.agent.session_store import set_last_exported_files
from app.core.reports.report_service import export_all_reports

initialize_session_state()

st.title("Reports")
st.write(
    "Export the latest workflow result to local JSON, Markdown, and Excel files, "
    "including confirmed outputs when review overrides are available."
)

result = st.session_state.get("workflow_result")
if result is None:
    st.warning("No workflow result is available yet. Please run diagnosis first.")
else:
    current_file = st.session_state.get("workflow_result_file_path") or "unknown_input"
    st.caption(f"Current result source: {current_file}")
    if result.mapping_results:
        st.info("Current result includes standard mapping recommendations and extended report content.")
    if result.stg_suggestions:
        st.info("Current result also includes STG table and field structure suggestions.")
    if result.confirmed_mapping_results or result.confirmed_stg_suggestions:
        st.info("Current result includes confirmed review outputs and can export confirmed sheets.")

    if st.button("Export Reports", type="primary"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{Path(current_file).stem}_{timestamp}"

        try:
            report_paths = export_all_reports(result, str(REPORT_OUTPUT_DIR), base_name)
        except Exception as exc:
            st.error(f"Failed to export reports: {exc}")
        else:
            set_last_exported_files(ensure_agent_shell_session_id(), report_paths)
            st.session_state["latest_report_paths"] = report_paths
            history = list(st.session_state.get("report_export_history", []))
            history.append(report_paths)
            st.session_state["report_export_history"] = history[-10:]
            st.success("Reports exported successfully.")

latest_report_paths = st.session_state.get("latest_report_paths", {})
if latest_report_paths:
    st.subheader("Latest Exported Files")
    for report_type, report_path in latest_report_paths.items():
        path = Path(report_path)
        st.write(f"- `{report_type}`: {report_path}")
        if path.exists():
            mime = {
                "json": "application/json",
                "markdown": "text/markdown",
                "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }.get(report_type, "application/octet-stream")
            st.download_button(
                label=f"Download {report_type}",
                data=path.read_bytes(),
                file_name=path.name,
                mime=mime,
                key=f"download_{report_type}_{path.name}",
            )

history = st.session_state.get("report_export_history", [])
if history:
    st.subheader("Recent Export History")
    for export_index, export_paths in enumerate(reversed(history), start=1):
        st.write(f"Export {export_index}")
        for report_type, report_path in export_paths.items():
            st.write(f"- `{report_type}`: {report_path}")

"""Natural-language task interpreter page."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.intent.intent_task_service import (
    interpret_and_build_request,
    interpret_and_run_task,
)
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_intent_overview
from app.ui.result_overview import render_result_overview
from app.ui.workbench_cache import review_summary_to_dataframe

initialize_session_state()

st.title("Intent Runner")
st.write(
    "Enter a short natural-language governance task, inspect how it maps to a "
    "workflow profile, and optionally run it through the existing router."
)

uploaded_file_path = st.session_state.get("uploaded_file_path")
default_file_path = uploaded_file_path or ""

task_text = st.text_area(
    "Task Text",
    value="Help me inspect this metadata file and export reports",
    height=120,
    help="Example: Run standard mapping and export reports",
)
file_path = st.text_input(
    "File Path",
    value=default_file_path,
    help="If you already uploaded a file, its saved local path is prefilled here.",
)
execution_mode = st.radio(
    "Execution Mode",
    options=["Interpret only", "Interpret and run"],
    horizontal=True,
)

if st.button("Execute Intent", type="primary"):
    try:
        with st.spinner("Interpreting task request..."):
            if execution_mode == "Interpret only":
                execution_result = interpret_and_build_request(
                    text=task_text,
                    file_path=file_path or None,
                )
            else:
                execution_result = interpret_and_run_task(
                    text=task_text,
                    file_path=file_path or None,
                )
    except Exception as exc:
        st.error(f"Failed to process natural-language task: {exc}")
    else:
        st.session_state["latest_intent_execution_result"] = execution_result
        if execution_result.task_response is not None:
            st.session_state["governance_task_response"] = execution_result.task_response
            if hasattr(execution_result.task_response.result, "status"):
                st.session_state["workflow_result"] = execution_result.task_response.result
                st.session_state["workflow_result_file_path"] = (
                    execution_result.task_request.file_path
                )
            if execution_result.task_response.exported_files:
                st.session_state["latest_report_paths"] = (
                    execution_result.task_response.exported_files
                )
                history = list(st.session_state.get("report_export_history", []))
                history.append(execution_result.task_response.exported_files)
                st.session_state["report_export_history"] = history[-10:]
        st.success("Intent processing completed.")

execution_result = st.session_state.get("latest_intent_execution_result")
if execution_result is not None:
    render_result_overview(
        build_intent_overview(execution_result)
    )
    st.subheader("任务请求")
    st.json(execution_result.task_request.model_dump())

    interpreted_intent = execution_result.interpreted_intent
    render_explanation_block(
        "意图解释",
        summary=interpreted_intent.message,
        details=[
            ("匹配意图", interpreted_intent.matched_intent_name or "fallback"),
            ("匹配方案", interpreted_intent.matched_profile_name),
            ("匹配来源", interpreted_intent.match_source),
            ("关键词", interpreted_intent.matched_keywords),
            ("回退解析", interpreted_intent.fallback_used),
            ("本地相似度", interpreted_intent.nlp_similarity),
        ],
        confidence=interpreted_intent.confidence,
        next_step="如果结果可用，可以直接运行；如果不对，回到上传页或诊断页补充文件上下文。",
    )
    st.json(interpreted_intent.inferred_parameters)

    if execution_result.task_response is not None:
        task_response = execution_result.task_response
        render_explanation_block(
            "任务结果",
            summary=task_response.message,
            details=[
                ("方案", task_response.profile_name),
                ("执行阶段", task_response.stages_executed),
                ("状态", task_response.status),
            ],
            next_step="下一步可以去 Review 查看人工覆盖，或去 Reports 导出结果。",
        )

        workflow_result = task_response.result
        if hasattr(workflow_result, "issue_count"):
            metric_issue, metric_mapping, metric_stg = st.columns(3)
            metric_issue.metric("Issue Count", workflow_result.issue_count)
            metric_mapping.metric("Mapping Count", len(workflow_result.mapping_results))
            metric_stg.metric("STG Count", len(workflow_result.stg_field_suggestions))

            if workflow_result.review_summary is not None:
                st.subheader("Review Summary")
                review_summary_df = review_summary_to_dataframe(
                    workflow_result.review_summary
                )
                if not review_summary_df.empty:
                    st.dataframe(review_summary_df, use_container_width=True)

        if task_response.exported_files:
            st.subheader("Exported Files")
            st.json(task_response.exported_files)

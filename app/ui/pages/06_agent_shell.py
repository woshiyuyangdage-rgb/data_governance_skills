"""Agent shell page for plan preview, validation, confirmation, and execution."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_utils import ensure_agent_shell_session_id

ensure_project_root_on_path()

from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent.session_store import get_session, set_last_uploaded_file
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_agent_overview
from app.ui.result_overview import render_result_overview
from app.ui.workbench_cache import (
    quality_rules_to_dataframe,
    review_summary_to_dataframe,
)

initialize_session_state()

service = AgentShellService()

st.title("Agent Shell")
st.write(
    "Preview a rule-based execution plan, validate required parameters, and run "
    "only after the shell policy allows it."
)

uploaded_file_path = st.session_state.get("uploaded_file_path")
default_session_id = st.session_state.get("agent_shell_session_id") or ""
active_session_id = ensure_agent_shell_session_id()
if uploaded_file_path:
    set_last_uploaded_file(active_session_id, uploaded_file_path)
    st.caption(
        f"Current uploaded file is available for session autofill: {uploaded_file_path}"
    )

task_text = st.text_area(
    "Task Text",
    value="Help me inspect this file",
    height=120,
    key="agent_shell_text_input",
)
st.caption(
    "Examples: Help me inspect this file | Use the uploaded file for standard mapping and export reports | Generate STG suggestions from the last file | Recommend quality rules from the current file | Rerun with confirmed results"
)
file_path = st.text_input(
    "File Path",
    value="",
    help="Leave blank when you want the context resolver to reuse the current session file safely.",
    key="agent_shell_file_path_input",
)
session_id_input = st.text_input(
    "Session ID",
    value=default_session_id or active_session_id,
    help="Leave blank to create a new local session automatically.",
    key="agent_shell_session_id_input",
)

preview_col, run_col = st.columns(2)
preview_clicked = preview_col.button("Preview Plan", type="primary")
run_clicked = run_col.button("Confirm and Run")

if preview_clicked:
    try:
        with st.spinner("Building execution plan..."):
            shell_result = service.interpret_to_plan(
                text=task_text,
                file_path=file_path or None,
                session_id=session_id_input or None,
            )
    except Exception as exc:
        st.error(f"Failed to build execution plan: {exc}")
    else:
        st.session_state["latest_agent_shell_result"] = shell_result
        st.session_state["agent_shell_session_id"] = shell_result.session_id
        st.success("Execution plan preview generated.")

if run_clicked:
    try:
        with st.spinner("Evaluating plan and execution policy..."):
            shell_result = service.confirm_and_run(
                text=task_text,
                file_path=file_path or None,
                session_id=session_id_input or None,
                force_run=False,
            )
    except Exception as exc:
        st.error(f"Failed to process agent shell request: {exc}")
    else:
        st.session_state["latest_agent_shell_result"] = shell_result
        st.session_state["agent_shell_session_id"] = shell_result.session_id
        if shell_result.task_response is not None:
            st.session_state["governance_task_response"] = shell_result.task_response
            st.session_state["workflow_result"] = shell_result.task_response.result
            st.session_state["workflow_result_file_path"] = shell_result.task_request.file_path
            if shell_result.task_response.exported_files:
                st.session_state["latest_report_paths"] = shell_result.task_response.exported_files
                history = list(st.session_state.get("report_export_history", []))
                history.append(shell_result.task_response.exported_files)
                st.session_state["report_export_history"] = history[-10:]
        if shell_result.status == "preview_requires_confirmation":
            st.warning(shell_result.message)
        elif shell_result.status == "validation_failed":
            st.error(shell_result.message)
        elif shell_result.status == "executed_successfully":
            st.success(shell_result.message)
        else:
            st.info(shell_result.message)

shell_result = st.session_state.get("latest_agent_shell_result")
if shell_result is not None:
    render_result_overview(build_agent_overview(shell_result))

    plan = shell_result.execution_plan
    interpreted_intent = shell_result.interpreted_intent
    render_explanation_block(
        "计划预览",
        summary=plan.summary,
        details=[
            ("会话 ID", shell_result.session_id),
            ("匹配方案", interpreted_intent.matched_profile_name),
            ("匹配来源", interpreted_intent.match_source),
            ("阶段", plan.stages),
            ("需要确认", plan.requires_confirmation),
            ("验证通过", plan.validation_passed),
            ("输出模式", plan.suggested_output_mode or "N/A"),
        ],
        confidence=interpreted_intent.confidence,
        next_step=(
            "如果计划需要确认，先检查验证说明；如果没有问题，可以直接执行。"
        ),
    )

    resolved_context = shell_result.resolved_context
    if resolved_context is not None:
        render_explanation_block(
            "解析出的上下文",
            details=[
                ("文件路径", resolved_context.resolved_file_path or "N/A"),
                ("输出目录", resolved_context.resolved_output_dir or "N/A"),
                ("解析来源", resolved_context.resolved_from),
                ("参考命中", resolved_context.reference_matches),
                ("自动补全", shell_result.resolution_applied),
                ("歧义检测", resolved_context.ambiguity_detected),
            ],
            evidence=resolved_context.messages,
            next_step="确认自动补全是否合理，再决定是否强制执行。",
        )
        if resolved_context.autofilled_parameters:
            st.json(resolved_context.autofilled_parameters)

    st.subheader("验证说明")
    if plan.validation_messages:
        for message in plan.validation_messages:
            st.write(f"- {message}")
    else:
        st.info("No validation warnings.")

    st.subheader("任务请求")
    st.json(shell_result.task_request.model_dump())

    if plan.requires_confirmation and shell_result.task_response is None:
        if st.button("Force Run"):
            try:
                with st.spinner("Force running the planned workflow..."):
                    forced_result = service.confirm_and_run(
                        text=st.session_state.get("agent_shell_text_input", task_text),
                        file_path=st.session_state.get(
                            "agent_shell_file_path_input",
                            file_path or None,
                        )
                        or None,
                        session_id=shell_result.session_id,
                        force_run=True,
                    )
            except Exception as exc:
                st.error(f"Failed to force run the planned workflow: {exc}")
            else:
                st.session_state["latest_agent_shell_result"] = forced_result
                st.session_state["agent_shell_session_id"] = forced_result.session_id
                if forced_result.task_response is not None:
                    st.session_state["governance_task_response"] = forced_result.task_response
                    st.session_state["workflow_result"] = forced_result.task_response.result
                    st.session_state["workflow_result_file_path"] = (
                        forced_result.task_request.file_path
                    )
                    if forced_result.task_response.exported_files:
                        st.session_state["latest_report_paths"] = (
                            forced_result.task_response.exported_files
                        )
                        history = list(st.session_state.get("report_export_history", []))
                        history.append(forced_result.task_response.exported_files)
                        st.session_state["report_export_history"] = history[-10:]
                if forced_result.status == "executed_successfully":
                    st.success(forced_result.message)
                else:
                    st.info(forced_result.message)

    if shell_result.task_response is not None:
        task_response = shell_result.task_response
        workflow_result = task_response.result

        render_explanation_block(
            "执行结果",
            summary=task_response.message,
            details=[
                ("状态", task_response.status),
                ("执行阶段", task_response.stages_executed),
            ],
            next_step="如果结果已确认，可直接导出或去 Review 页面固化覆盖。",
        )

        metric_issue, metric_mapping, metric_stg, metric_quality = st.columns(4)
        metric_issue.metric("Issue Count", workflow_result.issue_count)
        metric_mapping.metric("Mapping Count", len(workflow_result.mapping_results))
        metric_stg.metric("STG Count", len(workflow_result.stg_field_suggestions))
        metric_quality.metric("Quality Rules", len(workflow_result.quality_rule_suggestions))

        if workflow_result.quality_rule_summary or workflow_result.quality_rule_suggestions:
            render_explanation_block(
                "质量规则推荐",
                summary=workflow_result.quality_rule_summary,
                next_step="建议先在 Quality Rules 页确认，再构建执行包。",
            )
            quality_rules_df = quality_rules_to_dataframe(
                workflow_result.quality_rule_suggestions
            )
            if not quality_rules_df.empty:
                st.dataframe(quality_rules_df, use_container_width=True)

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

resolved_session_id = st.session_state.get("agent_shell_session_id")
if resolved_session_id:
    session = get_session(resolved_session_id)
    if session is not None:
        st.subheader("Session Overview")
        st.write(f"Current Session ID: `{session.session_id}`")
        st.write(f"Recent Requests: `{len(session.recent_requests)}`")
        st.write(f"Recent Plans: `{len(session.recent_plans)}`")
        st.write(f"Last Trace ID: `{session.last_trace_id or 'N/A'}`")
        st.write(f"Last Uploaded File: `{session.last_uploaded_file_path or 'N/A'}`")
        st.write(
            f"Recent Uploaded Files: `{', '.join(session.recent_uploaded_files) or 'N/A'}`"
        )
        st.write(
            f"Recent Trace IDs: `{', '.join(session.recent_trace_ids) or 'N/A'}`"
        )
        if session.last_exported_files:
            st.subheader("Last Exported Files")
            st.json(session.last_exported_files)

        if session.recent_plans:
            st.subheader("Recent Plans")
            for index, recent_plan in enumerate(reversed(session.recent_plans), start=1):
                with st.expander(
                    f"Plan {index}: {recent_plan.profile_name}",
                    expanded=False,
                ):
                    st.write(f"Stages: `{', '.join(recent_plan.stages) or 'N/A'}`")
                    st.write(
                        f"Validation Passed: `{recent_plan.validation_passed}` | "
                        f"Requires Confirmation: `{recent_plan.requires_confirmation}`"
                    )
                    if recent_plan.summary:
                        st.caption(recent_plan.summary)

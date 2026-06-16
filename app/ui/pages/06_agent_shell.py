"""Agent shell page for plan preview, validation, confirmation, and execution."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.page_utils import (
    ensure_agent_shell_session_id,
    get_agent_shell_session_id,
    get_latest_agent_shell_result,
    get_uploaded_file_path,
    get_session_value,
    set_latest_agent_shell_result,
    set_task_response_state,
)

ensure_project_root_on_path()

from app.core.agent.agent_shell_service import AgentShellService
from app.core.agent.session_store import get_session, set_last_uploaded_file
from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_agent_overview
from app.ui.performance_helpers import render_json_section, render_lazy_dataframe_section
from app.ui.result_overview import build_tool_response_overview, render_result_overview
from app.ui.status_blocks import (
    render_bullet_list,
    render_key_value_block,
    render_metric_row,
    render_page_header,
)
from app.ui.workbench_cache import (
    quality_rules_to_dataframe,
    review_summary_to_dataframe,
)

initialize_session_state()

service = AgentShellService()

render_page_header(
    "Agent 控制台",
    "输入治理任务，预览或运行本地规则化 Agent。",
)

uploaded_file_path = get_uploaded_file_path()
default_session_id = get_agent_shell_session_id() or ""
active_session_id = ensure_agent_shell_session_id()
if uploaded_file_path:
    set_last_uploaded_file(active_session_id, uploaded_file_path)
    st.caption("当前输入文件已就绪，可直接使用“当前文件”类任务。")

task_text = st.text_area(
    "任务文本",
    value="快速诊断当前文件",
    height=120,
    key="agent_shell_text_input",
)

with st.expander("高级参数", expanded=False):
    file_path = st.text_input(
        "文件路径",
        value="",
        key="agent_shell_file_path_input",
    )
    session_id_input = st.text_input(
        "会话 ID",
        value=default_session_id or active_session_id,
        key="agent_shell_session_id_input",
    )

preview_col, run_col = st.columns(2)
preview_clicked = preview_col.button("预览计划", type="primary")
run_clicked = run_col.button("确认并运行")

if preview_clicked:
    try:
        with st.spinner("正在生成执行计划..."):
            shell_result = service.interpret_to_plan(
                text=task_text,
                file_path=file_path or None,
                session_id=session_id_input or None,
            )
    except Exception as exc:
        st.error(f"生成执行计划失败: {exc}")
    else:
        set_latest_agent_shell_result(shell_result)
        st.success("执行计划预览已生成。")

if run_clicked:
    try:
        with st.spinner("正在评估计划和执行策略..."):
            shell_result = service.confirm_and_run(
                text=task_text,
                file_path=file_path or None,
                session_id=session_id_input or None,
                force_run=False,
            )
    except Exception as exc:
        st.error(f"处理 Agent 请求失败: {exc}")
    else:
        set_latest_agent_shell_result(shell_result)
        if shell_result.task_response is not None:
            set_task_response_state(
                shell_result.task_response,
                file_path=shell_result.task_request.file_path,
            )
        if shell_result.status == "preview_requires_confirmation":
            st.warning(shell_result.message)
        elif shell_result.status == "validation_failed":
            st.error(shell_result.message)
        elif shell_result.status == "executed_successfully":
            st.success(shell_result.message)
        else:
            st.info(shell_result.message)

shell_result = get_latest_agent_shell_result()
if shell_result is not None:
    render_result_overview(build_agent_overview(shell_result))

    plan = shell_result.execution_plan
    interpreted_intent = shell_result.interpreted_intent
    with st.expander("执行计划明细", expanded=False):
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
            )

        render_bullet_list(
            "验证说明",
            plan.validation_messages,
            empty_message="暂无校验提示。",
        )

    if plan.requires_confirmation and shell_result.task_response is None:
        if st.button("强制运行"):
            try:
                with st.spinner("正在强制运行计划工作流..."):
                    forced_result = service.confirm_and_run(
                        text=get_session_value("agent_shell_text_input", task_text),
                        file_path=get_session_value(
                            "agent_shell_file_path_input",
                            file_path or None,
                        )
                        or None,
                        session_id=shell_result.session_id,
                        force_run=True,
                    )
            except Exception as exc:
                st.error(f"强制运行计划工作流失败: {exc}")
            else:
                set_latest_agent_shell_result(forced_result)
                if forced_result.task_response is not None:
                    set_task_response_state(
                        forced_result.task_response,
                        file_path=forced_result.task_request.file_path,
                    )
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
            next_step="如果结果已确认，可直接导出或去评审页固化覆盖。",
        )

        render_metric_row(
            [
                ("问题数", workflow_result.issue_count),
                ("映射数", len(workflow_result.mapping_results)),
                ("STG 数", len(workflow_result.stg_field_suggestions)),
                ("质量规则", len(workflow_result.quality_rule_suggestions)),
            ],
        )

        if workflow_result.quality_rule_summary or workflow_result.quality_rule_suggestions:
            render_explanation_block(
                "质量规则推荐",
                summary=workflow_result.quality_rule_summary,
                next_step="建议先在质量规则页确认，再构建执行包。",
            )
            quality_rules_df = quality_rules_to_dataframe(
                workflow_result.quality_rule_suggestions
            )
            if not quality_rules_df.empty:
                render_lazy_dataframe_section(
                    "质量规则推荐",
                    quality_rules_df,
                    compact=True,
                    key_prefix="agent_quality_rules",
                )

        if workflow_result.review_summary is not None:
            st.subheader("评审汇总")
            review_summary_df = review_summary_to_dataframe(
                workflow_result.review_summary
            )
            if not review_summary_df.empty:
                render_lazy_dataframe_section(
                    "评审汇总",
                    review_summary_df,
                    compact=True,
                    key_prefix="agent_review_summary",
                )

        if task_response.exported_files:
            render_json_section("导出文件", task_response.exported_files)

resolved_session_id = get_agent_shell_session_id()
if resolved_session_id:
    session = get_session(resolved_session_id)
    if session is not None:
        with st.expander("会话与历史", expanded=False):
            render_key_value_block(
                "会话总览",
                rows=[
                    ("当前会话 ID", session.session_id),
                    ("最近请求数", len(session.recent_requests)),
                    ("最近计划数", len(session.recent_plans)),
                    ("最近执行跟踪 ID", session.last_trace_id or "N/A"),
                ],
            )
            if session.last_tool_response is not None:
                render_result_overview(build_tool_response_overview(session.last_tool_response))

            if session.last_exported_files:
                render_json_section("最近导出文件", session.last_exported_files)

            if session.recent_plans:
                st.subheader("最近计划")
                for index, recent_plan in enumerate(reversed(session.recent_plans), start=1):
                    with st.expander(
                        f"计划 {index}: {recent_plan.profile_name}",
                        expanded=False,
                    ):
                        render_key_value_block(
                            None,
                            summary=recent_plan.summary,
                            rows=[
                                ("阶段", ", ".join(recent_plan.stages) or "N/A"),
                                ("校验通过", recent_plan.validation_passed),
                                ("需要确认", recent_plan.requires_confirmation),
                            ],
                        )

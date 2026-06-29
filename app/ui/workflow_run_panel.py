"""Reusable workflow-run panel for Streamlit pages."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from app.core.agent.session_store import (
    set_last_exported_files,
    set_last_task_context,
    set_last_uploaded_file,
)
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.governance_task_response import GovernanceTaskResponse
from app.core.models.workflow_profile import WorkflowProfile
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.orchestrator.task_service import run_governance_task
from app.ui.page_overview import build_workflow_overview
from app.ui.page_utils import (
    ensure_agent_shell_session_id,
    get_selected_workflow_profile,
    set_selected_workflow_profile,
    set_task_response_state,
)
from app.ui.result_overview import render_result_overview


def select_profile_name(
    profile_names: list[str],
    selected_profile_name: str | None,
    *,
    fallback: str = "metadata_diagnosis_only",
) -> str:
    """Return a usable workflow profile name from current UI state."""
    if selected_profile_name in profile_names:
        return selected_profile_name
    if fallback in profile_names:
        return fallback
    return profile_names[0] if profile_names else fallback


def review_replay_control_defaults(profile: WorkflowProfile) -> tuple[bool, bool]:
    """Return default value and disabled state for review replay."""
    if profile.name in {
        "diagnosis_mapping_stg_with_review",
        "diagnosis_mapping_stg_quality_with_review",
    }:
        return True, True
    if profile.supports_review_replay:
        return True, False
    return False, True


def run_workflow_and_store(
    *,
    file_path: str,
    profile_name: str,
    apply_review_replay: bool,
    export_reports: bool,
    runner: Callable[[GovernanceTaskRequest], GovernanceTaskResponse] = run_governance_task,
) -> GovernanceTaskResponse:
    """Run one workflow and persist its result for downstream UI pages."""
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, file_path)
    task_request = GovernanceTaskRequest(
        file_path=file_path,
        profile_name=profile_name,
        apply_review_replay=apply_review_replay,
        export_reports=export_reports,
    )
    task_response = runner(task_request)
    set_task_response_state(task_response, file_path=file_path)
    set_last_task_context(
        agent_session_id,
        task_request=task_request,
        task_response=task_response,
    )
    if task_response.exported_files:
        set_last_exported_files(agent_session_id, task_response.exported_files)
    return task_response


def render_workflow_run_panel(
    file_path: str,
    *,
    key_prefix: str = "workflow_run",
    title: str = "快捷运行工作流",
) -> GovernanceTaskResponse | None:
    """Render a compact workflow runner for the current input file."""
    enabled_profiles = list_enabled_profiles()
    profile_lookup = {profile.name: profile for profile in enabled_profiles}
    profile_names = list(profile_lookup.keys())
    if not profile_names:
        st.warning("当前没有可用的工作流方案。")
        return None

    st.subheader(title)
    st.caption(f"当前输入文件: {file_path}")

    selected_profile_name = select_profile_name(
        profile_names,
        get_selected_workflow_profile(),
    )
    selected_index = profile_names.index(selected_profile_name)
    selected_profile_name = st.selectbox(
        "工作流方案",
        options=profile_names,
        index=selected_index,
        format_func=lambda name: f"{name} - {profile_lookup[name].description}",
        key=f"{key_prefix}_profile",
    )
    set_selected_workflow_profile(selected_profile_name)
    selected_profile = profile_lookup[selected_profile_name]
    st.caption(
        f"已选阶段: {', '.join(selected_profile.stages)} | "
        f"支持评审回放={selected_profile.supports_review_replay}"
    )

    replay_default, replay_disabled = review_replay_control_defaults(selected_profile)
    option_col1, option_col2 = st.columns(2)
    with option_col1:
        apply_review_replay = st.checkbox(
            "应用评审回放",
            value=replay_default,
            disabled=replay_disabled,
            help="运行时回放已经保存的映射、STG、质量规则等人工确认结果。",
            key=f"{key_prefix}_apply_review_replay",
        )
    with option_col2:
        export_reports = st.checkbox(
            "运行后导出报告",
            value=False,
            help="运行成功后自动导出 JSON / Markdown / Excel 文件。",
            key=f"{key_prefix}_export_reports",
        )

    if not st.button("运行当前输入", type="primary", use_container_width=True, key=f"{key_prefix}_run"):
        return None

    try:
        with st.spinner("正在运行治理工作流..."):
            task_response = run_workflow_and_store(
                file_path=file_path,
                profile_name=selected_profile_name,
                apply_review_replay=apply_review_replay,
                export_reports=export_reports,
            )
    except Exception as exc:
        st.error(f"运行工作流失败: {exc}")
        return None

    if task_response.status == "success":
        st.success("工作流执行完成。")
    else:
        st.error(task_response.message)

    if task_response.result is not None and hasattr(task_response.result, "status"):
        render_result_overview(
            build_workflow_overview(
                task_response.result,
                title="运行结果总览",
                next_step="结果已写入当前会话，可以继续进入评审页处理人工确认，或进入报告页查看明细与导出。",
            )
        )
    return task_response

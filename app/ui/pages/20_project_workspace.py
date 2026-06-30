"""Governance project workspace page."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (  # noqa: E402
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
)

ensure_project_root_on_path()

from app.core.governance.project_workspace_insights_service import (  # noqa: E402
    build_project_run_timeline,
    compare_project_workspace_runs,
)
from app.core.governance.project_workspace_service import (  # noqa: E402
    attach_project_artifact,
    create_project_workspace,
    list_project_workspaces,
    load_project_workspace,
    rebuild_workspace_index,
    record_project_run,
    set_project_review_state,
    summarize_project_workspace,
)
from app.core.governance.project_workspace_sync_service import (  # noqa: E402
    sync_workflow_result_to_project_workspace,
)
from app.core.models.project_workspace import ProjectWorkspaceSummary  # noqa: E402
from app.core.models.workflow_result import WorkflowResult  # noqa: E402
from app.ui.performance_helpers import (  # noqa: E402
    records_to_dataframe,
    render_json_section,
    render_lazy_dataframe_section,
    render_records_dataframe_section,
)
from app.ui.status_blocks import (  # noqa: E402
    render_key_value_block,
    render_metric_row,
    render_page_header,
)

initialize_session_state()

WORKSPACE_SELECTION_KEY = "project_workspace_selected_id"


def _split_tags(value: str) -> list[str]:
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def _workspace_options(
    summaries: list[ProjectWorkspaceSummary],
) -> dict[str, ProjectWorkspaceSummary]:
    return {summary.workspace_id: summary for summary in summaries}


def _workflow_summary(result: WorkflowResult | None) -> dict[str, object]:
    if result is None:
        return {}
    return {
        "diagnosis_issues": len(result.issues or []),
        "mapping_recommendations": len(result.mapping_results or []),
        "stg_suggestions": len(result.stg_suggestions or []),
        "quality_rule_recommendations": len(result.quality_rule_suggestions or []),
        "governance_backlog_items": len(result.governance_backlog_items or []),
        "delivery_manifest_ready": result.governance_delivery_manifest is not None,
    }


def _guess_workflow_profile(result: WorkflowResult | None) -> str:
    if result is None:
        return "manual_record"
    if result.governance_delivery_manifest is not None:
        return "governance_delivery_package"
    if result.governance_backlog_items:
        return "governance_backlog"
    if result.readiness_scores or result.governance_work_package is not None:
        return "governance_readiness"
    if result.quality_rule_suggestions:
        return "quality_rule_recommendation"
    return "metadata_governance_workflow"


def _run_options(workspace_id: str | None) -> dict[str, str]:
    if not workspace_id:
        return {}
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        return {}
    return {
        run.run_id: f"{run.run_id} | {run.workflow_profile} | {run.status}"
        for run in reversed(workspace.runs)
    }


render_page_header(
    "治理项目工作区",
    "把一个治理项目下的运行记录、评审队列和交付物统一追踪。",
)

summaries = list_project_workspaces()
summary_lookup = _workspace_options(summaries)

create_tab, manage_tab = st.tabs(["创建工作区", "跟踪工作区"])

with create_tab:
    with st.form("create_project_workspace_form"):
        name = st.text_input("项目名称", value="")
        description = st.text_area("项目说明", value="", height=80)
        owner_role = st.text_input("责任角色", value="")
        domain_pack_name = st.text_input("领域治理包", value="")
        template_name = st.text_input("项目模板", value="")
        tags = st.text_input("标签", value="", help="多个标签用逗号分隔")
        notes = st.text_area("备注", value="", height=80)
        submitted = st.form_submit_button("创建工作区", type="primary")
    if submitted:
        if not name.strip():
            st.warning("请填写项目名称。")
        else:
            workspace = create_project_workspace(
                name.strip(),
                description=description.strip() or None,
                owner_role=owner_role.strip() or None,
                domain_pack_name=domain_pack_name.strip() or None,
                template_name=template_name.strip() or None,
                tags=_split_tags(tags),
                notes=notes.strip() or None,
            )
            st.session_state[WORKSPACE_SELECTION_KEY] = workspace.workspace_id
            st.success(f"已创建工作区：{workspace.workspace_id}")
            st.rerun()

with manage_tab:
    col_refresh, col_count = st.columns([1, 3])
    with col_refresh:
        if st.button("重建索引", use_container_width=True):
            summaries = rebuild_workspace_index()
            summary_lookup = _workspace_options(summaries)
            st.success("索引已重建。")
    with col_count:
        st.caption(f"当前共有 {len(summaries)} 个本地工作区。")

    if not summaries:
        st.info("暂无工作区。先创建工作区，再记录运行和交付物。")
        st.stop()

    selected_id = st.selectbox(
        "选择工作区",
        options=list(summary_lookup),
        format_func=lambda value: f"{summary_lookup[value].name} ({value})",
        key=WORKSPACE_SELECTION_KEY,
    )
    workspace = load_project_workspace(selected_id)
    summary = summarize_project_workspace(selected_id)
    if workspace is None or summary is None:
        st.error("工作区文件不存在或已损坏。可以尝试重建索引。")
        st.stop()

    render_metric_row(
        [
            ("运行次数", summary.run_count),
            ("待评审", summary.pending_review_count),
            ("交付物", summary.artifact_count),
            ("最近状态", summary.last_run_status),
        ]
    )
    render_key_value_block(
        "工作区概况",
        rows=[
            ("工作区 ID", workspace.workspace_id),
            ("项目名称", workspace.name),
            ("状态", workspace.status),
            ("责任角色", workspace.owner_role),
            ("领域治理包", workspace.domain_pack_name),
            ("项目模板", workspace.template_name),
            ("标签", ", ".join(workspace.tags)),
            ("更新时间", workspace.updated_at),
        ],
    )
    if workspace.description:
        st.caption(workspace.description)

    record_tab, insight_tab, review_tab, artifact_tab, detail_tab = st.tabs(
        ["记录运行", "运行趋势", "评审队列", "交付物", "明细"]
    )

    with record_tab:
        current_result = get_workflow_result()
        input_file_path = get_current_input_file_path()
        default_summary = _workflow_summary(current_result)
        sync_col, sync_hint_col = st.columns([1, 2])
        with sync_col:
            sync_current = st.button(
                "同步当前工作流结果",
                type="primary",
                use_container_width=True,
                disabled=current_result is None,
            )
        with sync_hint_col:
            st.caption("自动记录运行，并同步评审队列、规则导出、执行包、确认工作簿和交付包。")
        if sync_current and current_result is not None:
            sync_result = sync_workflow_result_to_project_workspace(
                selected_id,
                current_result,
                workflow_profile=_guess_workflow_profile(current_result),
                input_file_path=input_file_path,
            )
            st.success(
                "已同步当前工作流结果："
                f"{sync_result['attached_artifact_count']} 个交付物，"
                f"{sync_result['synced_review_queue_count']} 个评审队列。"
            )
            st.rerun()
        with st.form("record_workspace_run_form"):
            workflow_profile = st.text_input(
                "工作流类型",
                value=_guess_workflow_profile(current_result),
            )
            run_status = st.selectbox(
                "运行状态",
                options=["success", "partial", "failed", "manual"],
                index=0,
            )
            run_input_path = st.text_input("输入文件", value=input_file_path or "")
            run_notes = st.text_area("运行备注", value="", height=80)
            use_current_summary = st.checkbox(
                "带入当前工作流摘要",
                value=bool(default_summary),
            )
            submitted_run = st.form_submit_button("记录运行", type="primary")
        if submitted_run:
            run = record_project_run(
                selected_id,
                workflow_profile=workflow_profile.strip() or "manual_record",
                status=run_status,
                input_file_path=run_input_path.strip() or None,
                result_summary=default_summary if use_current_summary else {},
                notes=run_notes.strip() or None,
            )
            st.success(f"已记录运行：{run.run_id}")
            st.rerun()
        render_json_section(
            "当前工作流摘要",
            default_summary,
            compact=True,
            empty_message="当前会话暂无工作流结果。",
        )

    with insight_tab:
        timeline = build_project_run_timeline(selected_id)
        timeline_rows = timeline.get("runs", [])
        if timeline_rows:
            render_lazy_dataframe_section(
                "运行趋势",
                records_to_dataframe(timeline_rows),
                compact=True,
                key_prefix="workspace_run_timeline",
            )
        else:
            st.info("暂无运行趋势。先记录或同步一次工作流结果。")

        if len(workspace.runs) >= 2:
            run_lookup = {
                run.run_id: f"{run.created_at or 'N/A'} | {run.workflow_profile} | {run.status}"
                for run in workspace.runs
            }
            compare_cols = st.columns(2)
            with compare_cols[0]:
                baseline_run_id = st.selectbox(
                    "基准运行",
                    options=list(run_lookup),
                    format_func=lambda value: run_lookup[value],
                    key="workspace_compare_baseline_run",
                )
            with compare_cols[1]:
                target_run_id = st.selectbox(
                    "目标运行",
                    options=list(run_lookup),
                    index=len(run_lookup) - 1,
                    format_func=lambda value: run_lookup[value],
                    key="workspace_compare_target_run",
                )
            comparison = compare_project_workspace_runs(
                selected_id,
                baseline_run_id=baseline_run_id,
                target_run_id=target_run_id,
            )
            render_records_dataframe_section(
                "运行对比",
                comparison.get("metric_deltas", []),
                empty_message="暂无可对比的运行指标。",
                key_prefix="workspace_run_comparison",
            )
            render_json_section(
                "对比 JSON",
                comparison,
                use_expander=True,
                compact=True,
            )
        else:
            st.info("至少需要 2 次运行才能做前后对比。")

    with review_tab:
        with st.form("workspace_review_state_form"):
            queue_name = st.selectbox(
                "评审队列",
                options=[
                    "standard_mapping",
                    "stg_structure",
                    "quality_rules",
                    "governance_backlog",
                    "delivery_confirmation",
                    "manual_review",
                ],
            )
            pending_count = st.number_input("待处理", min_value=0, value=0, step=1)
            accepted_count = st.number_input("已接受", min_value=0, value=0, step=1)
            edited_count = st.number_input("已编辑", min_value=0, value=0, step=1)
            rejected_count = st.number_input("已拒绝", min_value=0, value=0, step=1)
            confirmation_count = st.number_input(
                "待业务确认",
                min_value=0,
                value=0,
                step=1,
            )
            submitted_review = st.form_submit_button("更新评审状态", type="primary")
        if submitted_review:
            state = set_project_review_state(
                selected_id,
                queue_name=queue_name,
                pending_count=int(pending_count),
                accepted_count=int(accepted_count),
                edited_count=int(edited_count),
                rejected_count=int(rejected_count),
                needs_business_confirmation_count=int(confirmation_count),
            )
            st.success(f"已更新评审队列：{state.queue_name}")
            st.rerun()

    with artifact_tab:
        run_lookup = _run_options(selected_id)
        with st.form("workspace_artifact_form"):
            artifact_type = st.selectbox(
                "交付物类型",
                options=[
                    "report",
                    "confirmation_workbook",
                    "execution_package",
                    "delivery_package",
                    "manifest",
                    "evidence",
                    "other",
                ],
            )
            artifact_path = st.text_input("本地路径", value="")
            artifact_label = st.text_input("显示名称", value="")
            source_run_id = st.selectbox(
                "关联运行",
                options=[""] + list(run_lookup),
                format_func=lambda value: "不关联" if not value else run_lookup[value],
            )
            submitted_artifact = st.form_submit_button("登记交付物", type="primary")
        if submitted_artifact:
            if not artifact_path.strip():
                st.warning("请填写交付物本地路径。")
            else:
                artifact = attach_project_artifact(
                    selected_id,
                    artifact_type=artifact_type,
                    path=artifact_path.strip(),
                    label=artifact_label.strip() or None,
                    source_run_id=source_run_id or None,
                )
                st.success(f"已登记交付物：{artifact.artifact_id}")
                st.rerun()

    with detail_tab:
        render_records_dataframe_section(
            "运行记录",
            workspace.runs,
            empty_message="暂无运行记录。",
            key_prefix="workspace_runs",
        )
        render_records_dataframe_section(
            "评审队列",
            workspace.review_states,
            empty_message="暂无评审状态。",
            key_prefix="workspace_reviews",
        )
        render_records_dataframe_section(
            "交付物",
            workspace.artifacts,
            empty_message="暂无交付物。",
            key_prefix="workspace_artifacts",
        )
        render_json_section(
            "工作区 JSON",
            workspace,
            use_expander=True,
            compact=True,
        )

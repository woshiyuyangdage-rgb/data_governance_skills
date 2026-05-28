"""Governance backlog tracking page."""

import json
from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
    set_workflow_result_state,
)

ensure_project_root_on_path()

import app.core.governance.backlog_store as backlog_store
from app.core.governance.backlog_tracking_service import GovernanceBacklogTrackingService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import run_full_governance_backlog_package_from_file
from app.ui.page_overview import build_workflow_overview
from app.ui.result_overview import render_result_overview
from app.ui.workbench_cache import (
    backlog_summary_to_dataframe,
    governance_backlog_items_to_dataframe,
)
from app.ui.performance_helpers import (
    render_dataframe_multiselect_filter,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_metric_row, render_page_header

initialize_session_state()

render_page_header(
    "治理待办",
    "构建、持久化、筛选和更新本地治理待办。",
)


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()
service = GovernanceBacklogTrackingService()
BACKLOG_STATUS_LABELS = {
    "proposed": "待确认",
    "accepted": "已接受",
    "in_progress": "处理中",
    "blocked": "阻塞",
    "completed": "已完成",
    "dropped": "已放弃",
}

col_build, col_persist, col_export = st.columns(3)
with col_build:
    if st.button("构建治理待办", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("正在运行完整待办流程..."):
                    result = run_full_governance_backlog_package_from_file(uploaded_file_path)
            except Exception as exc:
                st.error(f"构建待办失败: {exc}")
            else:
                set_workflow_result_state(result, file_path=uploaded_file_path)
                st.success("治理待办已构建。")
        elif result is not None:
            items, summary = service.build_backlog_from_work_package(
                workflow_result=result
            )
            result.governance_backlog_items = items
            result.backlog_summary = summary
            set_workflow_result_state(result)
            st.success("已基于当前结果构建治理待办。")
        else:
            st.warning("请先运行就绪度/整改流程，或提供已上传文件。")

with col_persist:
    if st.button("保存待办"):
        current_result: WorkflowResult | None = get_workflow_result()
        if current_result is None or not current_result.governance_backlog_items:
            st.warning("请先构建待办再保存。")
        else:
            save_result = service.persist_backlog_items(
                current_result.governance_backlog_items,
                append=True,
            )
            st.success(f"已保存 {save_result['saved_count']} 条待办。")

with col_export:
    if st.button("导出待办 JSON"):
        items = backlog_store.list_backlog_items()
        summary = service.summarize_backlog(items)
        output_dir = PROJECT_ROOT / "outputs" / "governance_backlog"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "governance_backlog_export.json"
        output_path.write_text(
            json.dumps(
                {
                    "items": [item.model_dump() for item in items],
                    "summary": summary.model_dump(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        st.success(f"待办已导出到 {output_path}")

persisted_items = backlog_store.list_backlog_items()
current_items = (
    result.governance_backlog_items if result is not None and result.governance_backlog_items else []
)
display_items = persisted_items or current_items
summary = service.summarize_backlog(display_items)

if result is not None:
    render_result_overview(
        build_workflow_overview(
            result,
            title="治理待办总览",
            next_step="先确认待办，再做持久化或状态更新。",
        )
    )

render_metric_row(
        [
        ("待办数", summary.total_items),
        ("阻塞", summary.blocked_count),
        ("已完成", summary.completed_count),
        ("责任角色", len(summary.by_owner_role)),
    ],
)

st.subheader("待办汇总")
summary_df = backlog_summary_to_dataframe(summary)
if not summary_df.empty:
    render_lazy_dataframe_section(
        "待办汇总",
        summary_df,
        compact=True,
        key_prefix="backlog_summary",
    )

st.subheader("待办明细")
items_df = governance_backlog_items_to_dataframe(display_items)
items_df = render_dataframe_multiselect_filter(items_df, "status", "筛选状态")
items_df = render_dataframe_multiselect_filter(items_df, "priority", "筛选优先级")
items_df = render_dataframe_multiselect_filter(
    items_df,
    "owner_role",
    "筛选责任角色",
)
items_df = render_dataframe_multiselect_filter(items_df, "gap_type", "筛选缺口类型")
if not items_df.empty:
    render_lazy_dataframe_section(
        "待办明细",
        items_df,
        compact=True,
        key_prefix="backlog_items",
    )
else:
    st.info("暂无待办。")

st.subheader("更新待办状态")
if display_items:
    backlog_lookup = {item.backlog_id: item for item in display_items}
    selected_id = st.selectbox("待办项", options=sorted(backlog_lookup))
    new_status = st.selectbox(
        "新状态",
        options=["proposed", "accepted", "in_progress", "blocked", "completed", "dropped"],
        format_func=lambda value: BACKLOG_STATUS_LABELS.get(value, value),
    )
    note = st.text_input("更新备注", value="")
    if st.button("更新状态"):
        result_update = service.update_backlog_status(
            selected_id,
            new_status,
            note=note or None,
        )
        if result_update.status == "success":
            st.success(result_update.message)
        else:
            st.error(result_update.message)
else:
    st.info("请先保存待办，再更新状态。")

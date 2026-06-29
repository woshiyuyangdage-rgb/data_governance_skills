"""Governance portfolio and progress page."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
    record_report_paths,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.governance.backlog_sla_calculator import BacklogSlaCalculator
from app.core.governance.portfolio_aggregator import GovernancePortfolioAggregator
from app.core.governance.progress_snapshot_service import ProgressSnapshotService
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_portfolio_package_from_file,
)
from app.core.reports.report_service import export_all_reports
from app.ui.page_overview import build_workflow_overview
from app.ui.performance_helpers import (
    render_dataframe_multiselect_filter,
    render_lazy_dataframe_section,
)
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_metric_row, render_page_header
from app.ui.workbench_cache import (
    backlog_sla_statuses_to_dataframe,
    governance_backlog_items_to_dataframe,
    governance_portfolio_summary_to_dataframe,
    progress_snapshot_to_dataframe,
)

initialize_session_state()

render_page_header(
    "治理组合视图",
    "评估待办 SLA、组合工作量、逾期风险和进度快照。",
)


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()
snapshot_service = ProgressSnapshotService()

col_run, col_save, col_export = st.columns(3)
with col_run:
    if st.button("运行组合评估", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("正在运行治理组合流程..."):
                    result = run_full_governance_portfolio_package_from_file(
                        uploaded_file_path
                    )
            except Exception as exc:
                st.error(f"组合评估失败: {exc}")
            else:
                set_workflow_result_state(result, file_path=uploaded_file_path)
                st.success("治理组合评估完成。")
        elif result is not None and result.governance_backlog_items:
            result.backlog_sla_statuses = BacklogSlaCalculator().calculate(
                result.governance_backlog_items
            )
            result.governance_portfolio_summary = GovernancePortfolioAggregator().summarize(
                result.governance_backlog_items,
                readiness_scores=result.readiness_scores,
                backlog_sla_statuses=result.backlog_sla_statuses,
            )
            result.progress_snapshot = snapshot_service.build_progress_snapshot(
                result.governance_backlog_items,
                backlog_sla_statuses=result.backlog_sla_statuses,
                readiness_scores=result.readiness_scores,
            )
            set_workflow_result_state(result)
            st.success("已基于当前结果完成治理组合评估。")
        else:
            st.warning("请先构建待办，或提供已上传的元数据文件。")

with col_save:
    if st.button("保存进度快照"):
        current_result: WorkflowResult | None = get_workflow_result()
        if current_result is None or current_result.progress_snapshot is None:
            st.warning("请先运行组合评估再保存快照。")
        else:
            save_result = snapshot_service.save_progress_snapshot(
                current_result.progress_snapshot
            )
            st.success(f"快照已保存: {save_result['snapshot_id']}")

with col_export:
    if st.button("导出组合报告"):
        current_result: WorkflowResult | None = get_workflow_result()
        if current_result is None:
            st.warning("请先运行组合评估再导出。")
        else:
            output_dir = PROJECT_ROOT / "outputs" / "reports"
            paths = export_all_reports(
                current_result,
                str(output_dir),
                "governance_portfolio_report",
            )
            record_report_paths(paths)
            st.success(f"组合报告已导出: {paths['json']}")

current_result = get_workflow_result()
if current_result is None:
    st.info("请先运行组合评估以填充本页面。")
    st.stop()

render_result_overview(
    build_workflow_overview(
        current_result,
        title="治理组合总览",
        next_step="先看 SLA 和进展，再导出报告。",
    )
)

summary = current_result.governance_portfolio_summary
snapshot = current_result.progress_snapshot

render_metric_row(
    [
        ("待办数", summary.total_items if summary else 0),
        ("逾期", summary.overdue_count if summary else 0),
        ("阻塞", summary.blocked_count if summary else 0),
        ("责任角色", len(summary.owner_workload) if summary else 0),
    ],
)

st.subheader("治理组合汇总")
summary_df = governance_portfolio_summary_to_dataframe(summary)
if not summary_df.empty:
    render_lazy_dataframe_section(
        "治理组合汇总",
        summary_df,
        compact=True,
        key_prefix="portfolio_summary",
    )

st.subheader("进度快照")
snapshot_df = progress_snapshot_to_dataframe(snapshot)
if not snapshot_df.empty:
    render_lazy_dataframe_section(
        "进度快照",
        snapshot_df,
        compact=True,
        key_prefix="portfolio_snapshot",
    )

st.subheader("待办 SLA 状态")
sla_df = backlog_sla_statuses_to_dataframe(current_result.backlog_sla_statuses)
if not sla_df.empty:
    render_lazy_dataframe_section(
        "待办 SLA 状态",
        sla_df,
        compact=True,
        key_prefix="portfolio_sla",
    )
else:
    st.info("暂无 SLA 状态。")

st.subheader("待办明细")
items_df = governance_backlog_items_to_dataframe(current_result.governance_backlog_items)
sla_lookup = {
    status.backlog_id: status.model_dump()
    for status in current_result.backlog_sla_statuses
}
if not items_df.empty:
    items_df["sla_status"] = items_df["backlog_id"].map(
        lambda value: sla_lookup.get(value, {}).get("sla_status")
    )
    items_df["is_overdue"] = items_df["backlog_id"].map(
        lambda value: sla_lookup.get(value, {}).get("is_overdue", False)
    )
    items_df = render_dataframe_multiselect_filter(
        items_df,
        "owner_role",
        "筛选责任角色",
    )
    items_df = render_dataframe_multiselect_filter(items_df, "priority", "筛选优先级")
    items_df = render_dataframe_multiselect_filter(items_df, "status", "筛选状态")
    overdue_only = st.checkbox("只看逾期")
    if overdue_only:
        items_df = items_df[items_df["is_overdue"].fillna(False)]
    render_lazy_dataframe_section(
        "待办明细",
        items_df,
        compact=True,
        key_prefix="portfolio_backlog_items",
    )
else:
    st.info("暂无待办。")

st.subheader("责任角色工作量")
if summary is not None and summary.owner_workload:
    workload_df = pd.DataFrame(
        [
            {"owner_role": owner_role, **payload}
            for owner_role, payload in summary.owner_workload.items()
        ]
    )
    render_lazy_dataframe_section(
        "责任角色工作量",
        workload_df,
        compact=True,
        key_prefix="portfolio_owner_workload",
    )
else:
    st.info("暂无责任角色工作量汇总。")

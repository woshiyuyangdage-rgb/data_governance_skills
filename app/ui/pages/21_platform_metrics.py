"""Platform-wide local data metrics page."""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (  # noqa: E402
    ensure_project_root_on_path,
    initialize_session_state,
)

ensure_project_root_on_path()

from app.core.governance.platform_metrics_service import (
    collect_platform_metrics,  # noqa: E402
)
from app.ui.performance_helpers import (  # noqa: E402
    records_to_dataframe,
    render_json_section,
    render_lazy_dataframe_section,
)
from app.ui.status_blocks import render_metric_row, render_page_header  # noqa: E402

initialize_session_state()


def _format_bytes(value: object) -> str:
    try:
        size = float(value)
    except (TypeError, ValueError):
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.1f} {units[unit_index]}" if unit_index else f"{int(size)} B"


def _records_dataframe(records: list[object]) -> pd.DataFrame:
    dataframe = records_to_dataframe(records)
    return dataframe if isinstance(dataframe, pd.DataFrame) else pd.DataFrame()


def _render_distribution(title: str, records: list[object], key_prefix: str) -> None:
    st.subheader(title)
    dataframe = _records_dataframe(records)
    if dataframe.empty:
        st.info("暂无数据。")
        return
    chart_df = dataframe.set_index("name")["count"]
    st.bar_chart(chart_df)
    render_lazy_dataframe_section(
        title,
        dataframe,
        compact=True,
        key_prefix=key_prefix,
    )


def _csv_download_data(dataframe: pd.DataFrame) -> bytes:
    return dataframe.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def _render_health_signal(signal: object) -> None:
    severity = getattr(signal, "severity", "")
    title = getattr(signal, "title", "")
    detail = getattr(signal, "detail", "")
    action = getattr(signal, "recommended_action", None)
    message = f"**{title}**\n\n{detail}"
    if action:
        message = f"{message}\n\n建议：{action}"
    if severity == "high":
        st.error(message)
    elif severity == "medium":
        st.warning(message)
    elif severity == "low":
        st.info(message)
    else:
        st.success(message)


render_page_header(
    "平台数据总览",
    "统计本地平台沉淀的工作区、运行、评审、待办、审计 trace 和交付文件。",
)

filter_expander = st.expander("筛选与导出", expanded=True)
with filter_expander:
    filter_cols = st.columns(4)
    with filter_cols[0]:
        workspace_statuses = st.multiselect(
            "工作区状态",
            options=["active", "paused", "completed", "archived"],
        )
    with filter_cols[1]:
        backlog_statuses = st.multiselect(
            "待办状态",
            options=[
                "proposed",
                "accepted",
                "in_progress",
                "blocked",
                "completed",
                "dropped",
            ],
        )
    with filter_cols[2]:
        trace_statuses = st.multiselect(
            "Trace 状态",
            options=["success", "failed", "partial", "started"],
        )
    with filter_cols[3]:
        recent_activity_limit = st.number_input(
            "最近活动数",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
        )
    min_delivery_score = st.slider(
        "最低交付完整度",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )

if st.button("刷新统计", use_container_width=False):
    st.cache_data.clear()

metrics = collect_platform_metrics(
    workspace_statuses=workspace_statuses,
    backlog_statuses=backlog_statuses,
    trace_statuses=trace_statuses,
    recent_activity_limit=int(recent_activity_limit),
)
st.caption(f"统计时间：{metrics.generated_at}")

kpi_lookup = {item.name: item for item in metrics.kpis}
active_risk_count = sum(1 for signal in metrics.health_signals if signal.severity != "ok")
render_metric_row(
    [
        ("工作区", kpi_lookup["project_workspaces"].value),
        ("运行次数", kpi_lookup["workspace_runs"].value),
        ("待评审", kpi_lookup["pending_reviews"].value),
        ("交付物", kpi_lookup["workspace_artifacts"].value),
        ("待办", kpi_lookup["backlog_items"].value),
        ("Trace", kpi_lookup["execution_traces"].value),
        ("输出文件", kpi_lookup["output_files"].value),
        ("输出体量", _format_bytes(kpi_lookup["output_bytes"].value)),
        ("风险提示", active_risk_count),
    ],
    max_columns=4,
)

export_cols = st.columns(3)
with export_cols[0]:
    st.download_button(
        "下载统计 JSON",
        data=json.dumps(metrics.model_dump(), ensure_ascii=False, indent=2).encode(
            "utf-8"
        ),
        file_name="platform_metrics.json",
        mime="application/json",
        use_container_width=True,
    )
with export_cols[1]:
    st.download_button(
        "下载工作区 CSV",
        data=_csv_download_data(_records_dataframe(metrics.workspace_metrics)),
        file_name="platform_workspace_metrics.csv",
        mime="text/csv",
        use_container_width=True,
    )
with export_cols[2]:
    st.download_button(
        "下载最近活动 CSV",
        data=_csv_download_data(_records_dataframe(metrics.recent_activities)),
        file_name="platform_recent_activities.csv",
        mime="text/csv",
        use_container_width=True,
    )

overview_tab, health_tab, workspace_tab, backlog_tab, trace_tab, storage_tab, raw_tab = st.tabs(
    ["概览", "健康", "工作区", "待办", "Trace", "文件", "原始数据"]
)

with overview_tab:
    col_run, col_artifact = st.columns(2)
    with col_run:
        _render_distribution(
            "运行状态分布",
            metrics.run_status_distribution,
            "platform_run_status",
        )
    with col_artifact:
        _render_distribution(
            "交付物类型分布",
            metrics.artifact_type_distribution,
            "platform_artifact_type",
        )

    col_workspace, col_profile = st.columns(2)
    with col_workspace:
        _render_distribution(
            "工作区状态分布",
            metrics.workspace_status_distribution,
            "platform_workspace_status",
        )
    with col_profile:
        _render_distribution(
            "工作流类型分布",
            metrics.workflow_profile_distribution,
            "platform_workflow_profile",
        )

    render_lazy_dataframe_section(
        "最近活动",
        _records_dataframe(metrics.recent_activities),
        compact=True,
        key_prefix="platform_recent_activity",
    )

with health_tab:
    st.subheader("平台健康提示")
    for signal in metrics.health_signals:
        _render_health_signal(signal)
    render_lazy_dataframe_section(
        "健康信号明细",
        _records_dataframe(metrics.health_signals),
        compact=True,
        key_prefix="platform_health_signals",
    )

with workspace_tab:
    workspace_df = _records_dataframe(metrics.workspace_metrics)
    if not workspace_df.empty:
        workspace_df = workspace_df[
            workspace_df["delivery_completeness_score"] >= min_delivery_score
        ]
        workspace_df = workspace_df.sort_values(
            by=[
                "pending_review_count",
                "delivery_completeness_score",
                "run_count",
                "artifact_count",
            ],
            ascending=[False, True, False, False],
        )
        completeness_df = (
            workspace_df["delivery_completeness_level"]
            .value_counts()
            .rename_axis("name")
            .reset_index(name="count")
        )
        _render_distribution(
            "交付完整度等级分布",
            completeness_df.to_dict("records"),
            "platform_delivery_completeness",
        )
    render_lazy_dataframe_section(
        "工作区排行",
        workspace_df,
        empty_message="暂无项目工作区。",
        compact=True,
        key_prefix="platform_workspace_metrics",
    )

with backlog_tab:
    col_status, col_priority = st.columns(2)
    with col_status:
        _render_distribution(
            "待办状态分布",
            metrics.backlog_status_distribution,
            "platform_backlog_status",
        )
    with col_priority:
        _render_distribution(
            "待办优先级分布",
            metrics.backlog_priority_distribution,
            "platform_backlog_priority",
        )
    _render_distribution(
        "责任角色分布",
        metrics.backlog_owner_distribution,
        "platform_backlog_owner",
    )

with trace_tab:
    col_status, col_tool = st.columns(2)
    with col_status:
        _render_distribution(
            "Trace 状态分布",
            metrics.trace_status_distribution,
            "platform_trace_status",
        )
    with col_tool:
        _render_distribution(
            "工具调用分布",
            metrics.trace_tool_distribution,
            "platform_trace_tool",
        )

with storage_tab:
    inventory_df = _records_dataframe(metrics.output_inventory)
    if not inventory_df.empty:
        inventory_df["total_size"] = inventory_df["total_bytes"].map(_format_bytes)
    render_lazy_dataframe_section(
        "输出目录文件盘点",
        inventory_df,
        empty_message="暂无输出文件。",
        compact=True,
        key_prefix="platform_output_inventory",
    )
    if not inventory_df.empty:
        st.bar_chart(inventory_df.set_index("bucket")["file_count"])

with raw_tab:
    render_json_section(
        "平台统计 JSON",
        metrics,
        compact=True,
        use_expander=False,
    )

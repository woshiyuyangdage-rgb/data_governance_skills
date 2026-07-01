"""Aggregate local platform data metrics for dashboard views."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.audit import trace_store
from app.core.governance import backlog_store
from app.core.governance.project_workspace_service import (
    list_project_workspaces,
    load_project_workspace,
)
from app.core.models.execution_trace import ExecutionTrace
from app.core.models.platform_metrics import (
    PlatformDistributionItem,
    PlatformFileInventoryItem,
    PlatformHealthSignal,
    PlatformKpi,
    PlatformMetrics,
    PlatformRecentActivity,
    PlatformWorkspaceMetric,
)
from app.core.models.project_workspace import ProjectWorkspace
from app.core.utils.time_utils import utc_now_seconds

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RECENT_ACTIVITY_LIMIT = 20
TRACE_SCAN_LIMIT = 500
PENDING_REVIEW_WARNING_THRESHOLD = 10
OUTPUT_FILE_WARNING_THRESHOLD = 500
OUTPUT_SIZE_WARNING_THRESHOLD_BYTES = 200 * 1024 * 1024
DELIVERY_COMPLETENESS_WARNING_THRESHOLD = 50
DELIVERY_COMPLETENESS_COMPONENTS = {
    "run_record": "运行记录",
    "review_state": "评审状态",
    "any_artifact": "任意交付物",
    "confirmation_workbook": "确认工作簿",
    "execution_package": "执行包",
    "delivery_package": "交付包或 manifest",
}


def _distribution(counter: Counter[str]) -> list[PlatformDistributionItem]:
    return [
        PlatformDistributionItem(name=name, count=count)
        for name, count in counter.most_common()
    ]


def _safe_counter_value(value: object | None, fallback: str = "unknown") -> str:
    return str(value or fallback)


def _load_recent_traces(limit: int = TRACE_SCAN_LIMIT) -> list[ExecutionTrace]:
    trace_dir = trace_store.TRACE_DIR
    if not trace_dir.exists():
        return []
    traces: list[ExecutionTrace] = []
    try:
        paths = sorted(
            trace_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return []
    for path in paths[: max(0, limit)]:
        try:
            traces.append(
                ExecutionTrace.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            )
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return traces


def _scan_output_inventory() -> list[PlatformFileInventoryItem]:
    if not OUTPUTS_DIR.exists():
        return []
    buckets: dict[str, dict[str, int]] = {}
    try:
        paths = list(OUTPUTS_DIR.rglob("*"))
    except OSError:
        return []
    for path in paths:
        try:
            if not path.is_file():
                continue
            relative = path.relative_to(OUTPUTS_DIR)
            bucket = relative.parts[0] if len(relative.parts) > 1 else path.suffix or "root"
            record = buckets.setdefault(bucket, {"file_count": 0, "total_bytes": 0})
            record["file_count"] += 1
            record["total_bytes"] += path.stat().st_size
        except OSError:
            continue
    return [
        PlatformFileInventoryItem(
            bucket=bucket,
            file_count=record["file_count"],
            total_bytes=record["total_bytes"],
        )
        for bucket, record in sorted(
            buckets.items(),
            key=lambda item: (item[1]["file_count"], item[1]["total_bytes"]),
            reverse=True,
        )
    ]


def _recent_activity_sort_key(activity: PlatformRecentActivity) -> str:
    return activity.occurred_at or ""


def _counter_count(counter: Counter[str], *names: str) -> int:
    return sum(counter.get(name, 0) for name in names)


def _delivery_completeness(workspace: ProjectWorkspace | None) -> dict[str, Any]:
    if workspace is None:
        return {
            "score": 0,
            "level": "not_loaded",
            "missing_components": list(DELIVERY_COMPLETENESS_COMPONENTS.values()),
        }
    artifact_types = {artifact.artifact_type for artifact in workspace.artifacts}
    component_status = {
        "run_record": bool(workspace.runs),
        "review_state": bool(workspace.review_states),
        "any_artifact": bool(workspace.artifacts),
        "confirmation_workbook": "confirmation_workbook" in artifact_types,
        "execution_package": "execution_package" in artifact_types,
        "delivery_package": bool(
            artifact_types.intersection(
                {"delivery_package", "delivery_artifact", "manifest"}
            )
        ),
    }
    passed_count = sum(1 for passed in component_status.values() if passed)
    score = round(passed_count / len(component_status) * 100)
    if score >= 85:
        level = "complete"
    elif score >= 60:
        level = "mostly_complete"
    elif score > 0:
        level = "partial"
    else:
        level = "not_started"
    missing_components = [
        DELIVERY_COMPLETENESS_COMPONENTS[key]
        for key, passed in component_status.items()
        if not passed
    ]
    return {
        "score": score,
        "level": level,
        "missing_components": missing_components,
    }


def _build_health_signals(
    *,
    workspace_data: dict[str, Any],
    backlog_status_counter: Counter[str],
    trace_status_counter: Counter[str],
    output_file_count: int,
    output_total_bytes: int,
) -> list[PlatformHealthSignal]:
    signals: list[PlatformHealthSignal] = []
    failed_trace_count = _counter_count(trace_status_counter, "failed", "error")
    if failed_trace_count:
        signals.append(
            PlatformHealthSignal(
                severity="high",
                signal_type="trace_failure",
                title="存在失败的工具调用 Trace",
                detail=f"最近扫描到 {failed_trace_count} 条失败 Trace。",
                count=failed_trace_count,
                recommended_action="进入 Trace 分布查看失败工具，优先复查最近失败记录。",
            )
        )

    blocked_backlog_count = backlog_status_counter.get("blocked", 0)
    if blocked_backlog_count:
        signals.append(
            PlatformHealthSignal(
                severity="high",
                signal_type="blocked_backlog",
                title="存在阻塞治理待办",
                detail=f"当前有 {blocked_backlog_count} 条 blocked 待办。",
                count=blocked_backlog_count,
                recommended_action="在待办页确认阻塞原因、责任角色和下一步动作。",
            )
        )

    pending_review_count = int(workspace_data["total_pending_review"])
    if pending_review_count >= PENDING_REVIEW_WARNING_THRESHOLD:
        signals.append(
            PlatformHealthSignal(
                severity="medium",
                signal_type="pending_review_load",
                title="待评审负载较高",
                detail=f"项目工作区累计待评审 {pending_review_count} 项。",
                count=pending_review_count,
                recommended_action="按工作区排行优先处理待评审数最高的项目。",
            )
        )

    workspace_without_artifacts = [
        item
        for item in workspace_data["workspace_rows"]
        if item.run_count > 0 and item.artifact_count == 0
    ]
    if workspace_without_artifacts:
        signals.append(
            PlatformHealthSignal(
                severity="medium",
                signal_type="run_without_artifacts",
                title="部分工作区有运行但没有交付物",
                detail=f"{len(workspace_without_artifacts)} 个工作区已有运行记录但没有交付物。",
                count=len(workspace_without_artifacts),
                recommended_action="在项目工作区同步当前工作流结果或登记交付物。",
            )
        )

    low_completeness_workspaces = [
        item
        for item in workspace_data["workspace_rows"]
        if item.run_count > 0
        and item.delivery_completeness_score < DELIVERY_COMPLETENESS_WARNING_THRESHOLD
    ]
    if low_completeness_workspaces:
        signals.append(
            PlatformHealthSignal(
                severity="medium",
                signal_type="low_delivery_completeness",
                title="部分工作区交付完整度偏低",
                detail=(
                    f"{len(low_completeness_workspaces)} 个已有运行的工作区"
                    f"交付完整度低于 {DELIVERY_COMPLETENESS_WARNING_THRESHOLD}%。"
                ),
                count=len(low_completeness_workspaces),
                recommended_action="进入工作区排行，优先补齐缺失的评审状态和交付物。",
            )
        )

    if output_file_count >= OUTPUT_FILE_WARNING_THRESHOLD:
        signals.append(
            PlatformHealthSignal(
                severity="low",
                signal_type="large_output_file_count",
                title="outputs 文件数量较多",
                detail=f"outputs 目录下累计 {output_file_count} 个文件。",
                count=output_file_count,
                recommended_action="视情况运行本地清理命令或归档历史交付文件。",
            )
        )

    if output_total_bytes >= OUTPUT_SIZE_WARNING_THRESHOLD_BYTES:
        signals.append(
            PlatformHealthSignal(
                severity="low",
                signal_type="large_output_size",
                title="outputs 目录体量较大",
                detail=f"outputs 目录累计 {output_total_bytes} 字节。",
                count=output_total_bytes,
                recommended_action="检查文件盘点中体量最高的目录，清理临时或重复产物。",
            )
        )

    if not signals:
        signals.append(
            PlatformHealthSignal(
                severity="ok",
                signal_type="platform_health",
                title="未发现明显平台风险",
                detail="当前筛选范围内没有失败 Trace、阻塞待办或高待评审负载。",
                count=0,
                recommended_action="继续保持工作区运行和交付物同步。",
            )
        )
    return signals


def _normalized_filter(values: set[str] | list[str] | tuple[str, ...] | None) -> set[str]:
    return {str(value) for value in values or [] if str(value)}


def _matches_filter(value: object | None, selected: set[str]) -> bool:
    return not selected or _safe_counter_value(value) in selected


def _workspace_metrics_and_counters(
    *,
    workspace_statuses: set[str] | None = None,
) -> dict[str, Any]:
    summaries = list_project_workspaces()
    selected_workspace_statuses = workspace_statuses or set()
    workspace_rows: list[PlatformWorkspaceMetric] = []
    workspace_status_counter: Counter[str] = Counter()
    run_status_counter: Counter[str] = Counter()
    workflow_profile_counter: Counter[str] = Counter()
    artifact_type_counter: Counter[str] = Counter()
    recent_activities: list[PlatformRecentActivity] = []
    total_runs = 0
    total_artifacts = 0
    total_pending_review = 0

    for summary in summaries:
        if not _matches_filter(summary.status, selected_workspace_statuses):
            continue
        workspace = load_project_workspace(summary.workspace_id)
        completeness = _delivery_completeness(workspace)
        workspace_status_counter[_safe_counter_value(summary.status)] += 1
        total_runs += summary.run_count
        total_artifacts += summary.artifact_count
        total_pending_review += summary.pending_review_count
        workspace_rows.append(
            PlatformWorkspaceMetric(
                workspace_id=summary.workspace_id,
                name=summary.name,
                status=summary.status,
                owner_role=summary.owner_role,
                run_count=summary.run_count,
                artifact_count=summary.artifact_count,
                pending_review_count=summary.pending_review_count,
                delivery_completeness_score=completeness["score"],
                delivery_completeness_level=completeness["level"],
                missing_delivery_components=completeness["missing_components"],
                last_run_status=summary.last_run_status,
                updated_at=summary.updated_at,
            )
        )
        recent_activities.append(
            PlatformRecentActivity(
                activity_type="workspace",
                label=summary.name,
                status=summary.status,
                occurred_at=summary.updated_at,
                source_id=summary.workspace_id,
            )
        )
        if workspace is None:
            continue
        for run in workspace.runs:
            run_status_counter[_safe_counter_value(run.status)] += 1
            workflow_profile_counter[_safe_counter_value(run.workflow_profile)] += 1
        for artifact in workspace.artifacts:
            artifact_type_counter[_safe_counter_value(artifact.artifact_type)] += 1

    return {
        "workspace_rows": sorted(
            workspace_rows,
            key=lambda item: (
                item.pending_review_count,
                item.run_count,
                item.artifact_count,
            ),
            reverse=True,
        ),
        "workspace_status_counter": workspace_status_counter,
        "run_status_counter": run_status_counter,
        "workflow_profile_counter": workflow_profile_counter,
        "artifact_type_counter": artifact_type_counter,
        "recent_activities": recent_activities,
        "total_workspaces": len(workspace_rows),
        "total_runs": total_runs,
        "total_artifacts": total_artifacts,
        "total_pending_review": total_pending_review,
    }


def collect_platform_metrics(
    *,
    workspace_statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    backlog_statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    trace_statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    recent_activity_limit: int = RECENT_ACTIVITY_LIMIT,
    trace_scan_limit: int = TRACE_SCAN_LIMIT,
) -> PlatformMetrics:
    """Collect platform-wide metrics from local runtime stores."""
    selected_workspace_statuses = _normalized_filter(workspace_statuses)
    selected_backlog_statuses = _normalized_filter(backlog_statuses)
    selected_trace_statuses = _normalized_filter(trace_statuses)
    workspace_data = _workspace_metrics_and_counters(
        workspace_statuses=selected_workspace_statuses
    )
    backlog_items = [
        item
        for item in backlog_store.list_backlog_items()
        if _matches_filter(item.status, selected_backlog_statuses)
    ]
    traces = [
        trace
        for trace in _load_recent_traces(limit=trace_scan_limit)
        if _matches_filter(trace.status, selected_trace_statuses)
    ]
    output_inventory = _scan_output_inventory()

    backlog_status_counter = Counter(
        _safe_counter_value(item.status) for item in backlog_items
    )
    backlog_priority_counter = Counter(
        _safe_counter_value(item.priority) for item in backlog_items
    )
    backlog_owner_counter = Counter(
        _safe_counter_value(item.owner_role) for item in backlog_items
    )
    trace_status_counter = Counter(_safe_counter_value(trace.status) for trace in traces)
    trace_tool_counter = Counter(_safe_counter_value(trace.tool_name) for trace in traces)
    output_file_count = sum(item.file_count for item in output_inventory)
    output_total_bytes = sum(item.total_bytes for item in output_inventory)
    health_signals = _build_health_signals(
        workspace_data=workspace_data,
        backlog_status_counter=backlog_status_counter,
        trace_status_counter=trace_status_counter,
        output_file_count=output_file_count,
        output_total_bytes=output_total_bytes,
    )

    recent_activities = list(workspace_data["recent_activities"])
    recent_activities.extend(
        PlatformRecentActivity(
            activity_type="backlog",
            label=f"{item.object_name} | {item.gap_type}",
            status=item.status,
            occurred_at=item.updated_at or item.created_at,
            source_id=item.backlog_id,
        )
        for item in backlog_items
    )
    recent_activities.extend(
        PlatformRecentActivity(
            activity_type="trace",
            label=trace.tool_name,
            status=trace.status,
            occurred_at=trace.finished_at or trace.started_at,
            source_id=trace.trace_id,
        )
        for trace in traces[: max(0, int(recent_activity_limit))]
    )
    recent_activities = sorted(
        recent_activities,
        key=_recent_activity_sort_key,
        reverse=True,
    )[: max(0, int(recent_activity_limit))]

    kpis = [
        PlatformKpi(
            name="project_workspaces",
            value=workspace_data["total_workspaces"],
            description="Local governance project workspaces.",
        ),
        PlatformKpi(
            name="workspace_runs",
            value=workspace_data["total_runs"],
            description="Runs recorded in project workspaces.",
        ),
        PlatformKpi(
            name="pending_reviews",
            value=workspace_data["total_pending_review"],
            description="Pending or business-confirmation review items.",
        ),
        PlatformKpi(
            name="workspace_artifacts",
            value=workspace_data["total_artifacts"],
            description="Artifacts linked to project workspaces.",
        ),
        PlatformKpi(
            name="backlog_items",
            value=len(backlog_items),
            description="Persisted local governance backlog items.",
        ),
        PlatformKpi(
            name="execution_traces",
            value=len(traces),
            description="Recent local audit traces scanned.",
        ),
        PlatformKpi(
            name="output_files",
            value=output_file_count,
            description="Files under the local outputs directory.",
        ),
        PlatformKpi(
            name="output_bytes",
            value=output_total_bytes,
            description="Total bytes under the local outputs directory.",
        ),
    ]

    return PlatformMetrics(
        generated_at=utc_now_seconds(),
        kpis=kpis,
        workspace_metrics=workspace_data["workspace_rows"],
        workspace_status_distribution=_distribution(
            workspace_data["workspace_status_counter"]
        ),
        run_status_distribution=_distribution(workspace_data["run_status_counter"]),
        workflow_profile_distribution=_distribution(
            workspace_data["workflow_profile_counter"]
        ),
        artifact_type_distribution=_distribution(
            workspace_data["artifact_type_counter"]
        ),
        backlog_status_distribution=_distribution(backlog_status_counter),
        backlog_priority_distribution=_distribution(backlog_priority_counter),
        backlog_owner_distribution=_distribution(backlog_owner_counter),
        trace_status_distribution=_distribution(trace_status_counter),
        trace_tool_distribution=_distribution(trace_tool_counter),
        output_inventory=output_inventory,
        recent_activities=recent_activities,
        health_signals=health_signals,
    )

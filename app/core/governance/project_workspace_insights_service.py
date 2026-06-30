"""Project workspace timeline and run comparison helpers."""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Number
from typing import Any

from app.core.governance.project_workspace_service import load_project_workspace
from app.core.models.project_workspace import ProjectWorkspaceRun

METRIC_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("issue_count", ("issue_count", "diagnosis_issues")),
    ("task_count", ("task_count",)),
    ("mapping_count", ("mapping_count", "mapping_recommendations")),
    ("stg_suggestion_count", ("stg_suggestion_count", "stg_suggestions")),
    (
        "quality_rule_count",
        ("quality_rule_count", "quality_rule_recommendations"),
    ),
    ("confirmed_quality_rule_count", ("confirmed_quality_rule_count",)),
    ("readiness_score_count", ("readiness_score_count",)),
    ("ai_ready_score_count", ("ai_ready_score_count",)),
    ("backlog_item_count", ("backlog_item_count", "governance_backlog_items")),
)
LOWER_IS_BETTER_METRICS = {"issue_count", "backlog_item_count"}
HIGHER_IS_BETTER_METRICS = {
    "mapping_count",
    "stg_suggestion_count",
    "quality_rule_count",
    "confirmed_quality_rule_count",
    "readiness_score_count",
    "ai_ready_score_count",
    "artifact_count",
}


def _numeric_value(value: object) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, Number):
        return None
    return int(value) if float(value).is_integer() else float(value)


def _first_numeric(summary: dict[str, object], aliases: Iterable[str]) -> float | int | None:
    for key in aliases:
        value = _numeric_value(summary.get(key))
        if value is not None:
            return value
    return None


def extract_run_metrics(run: ProjectWorkspaceRun) -> dict[str, float | int]:
    """Extract stable numeric metrics from one workspace run."""
    metrics: dict[str, float | int] = {}
    for metric_name, aliases in METRIC_ALIASES:
        value = _first_numeric(run.result_summary, aliases)
        if value is not None:
            metrics[metric_name] = value
    metrics["artifact_count"] = len(run.artifact_ids)
    return metrics


def build_project_run_timeline(workspace_id: str) -> dict[str, object]:
    """Build a compact run timeline for one project workspace."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise KeyError(workspace_id)
    runs = [
        {
            "run_id": run.run_id,
            "created_at": run.created_at,
            "workflow_profile": run.workflow_profile,
            "status": run.status,
            **extract_run_metrics(run),
        }
        for run in workspace.runs
    ]
    return {
        "workspace_id": workspace.workspace_id,
        "name": workspace.name,
        "run_count": len(workspace.runs),
        "runs": runs,
    }


def _choose_run(
    runs: list[ProjectWorkspaceRun],
    run_id: str | None,
    *,
    default_index: int,
) -> ProjectWorkspaceRun | None:
    if not runs:
        return None
    if run_id is None:
        return runs[default_index]
    return next((run for run in runs if run.run_id == run_id), None)


def _direction(metric_name: str, delta: float | int) -> str:
    if delta == 0:
        return "unchanged"
    if metric_name in LOWER_IS_BETTER_METRICS:
        return "improved" if delta < 0 else "regressed"
    if metric_name in HIGHER_IS_BETTER_METRICS:
        return "improved" if delta > 0 else "regressed"
    return "changed"


def compare_project_workspace_runs(
    workspace_id: str,
    *,
    baseline_run_id: str | None = None,
    target_run_id: str | None = None,
) -> dict[str, Any]:
    """Compare two project workspace runs using extracted numeric metrics."""
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        raise KeyError(workspace_id)
    baseline = _choose_run(workspace.runs, baseline_run_id, default_index=0)
    target = _choose_run(workspace.runs, target_run_id, default_index=-1)
    if baseline is None or target is None:
        return {
            "workspace_id": workspace.workspace_id,
            "status": "insufficient_runs",
            "metric_deltas": [],
        }

    baseline_metrics = extract_run_metrics(baseline)
    target_metrics = extract_run_metrics(target)
    metric_names = sorted(set(baseline_metrics) | set(target_metrics))
    metric_deltas = []
    for metric_name in metric_names:
        baseline_value = baseline_metrics.get(metric_name, 0)
        target_value = target_metrics.get(metric_name, 0)
        delta = target_value - baseline_value
        metric_deltas.append(
            {
                "metric": metric_name,
                "baseline_value": baseline_value,
                "target_value": target_value,
                "delta": delta,
                "direction": _direction(metric_name, delta),
            }
        )

    return {
        "workspace_id": workspace.workspace_id,
        "status": "compared",
        "baseline_run_id": baseline.run_id,
        "target_run_id": target.run_id,
        "baseline_created_at": baseline.created_at,
        "target_created_at": target.created_at,
        "metric_deltas": metric_deltas,
    }

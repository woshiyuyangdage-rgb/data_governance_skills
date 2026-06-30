"""Sync workflow results into governance project workspaces."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from app.core.governance.project_workspace_service import (
    attach_project_artifact,
    load_project_workspace,
    record_project_run,
    set_project_review_state,
    summarize_project_workspace,
)
from app.core.models.project_workspace import ProjectWorkspaceArtifact
from app.core.models.workflow_result import WorkflowResult


def _workflow_summary(result: WorkflowResult) -> dict[str, object]:
    return {
        "input_table_count": result.input_table_count,
        "issue_count": result.issue_count or len(result.issues),
        "task_count": result.task_count or len(result.tasks),
        "mapping_count": len(result.mapping_results),
        "stg_suggestion_count": len(result.stg_suggestions),
        "quality_rule_count": len(result.quality_rule_suggestions),
        "confirmed_quality_rule_count": len(result.confirmed_quality_rules),
        "readiness_score_count": len(result.readiness_scores),
        "ai_ready_score_count": len(result.ai_ready_scores),
        "backlog_item_count": len(result.governance_backlog_items),
        "status": result.status,
        "message": result.message,
    }


def _artifact_label(*parts: object | None) -> str | None:
    visible = [str(part) for part in parts if part not in (None, "")]
    return " | ".join(visible) if visible else None


def _path_from_record(record: object, attr_name: str) -> str | None:
    value = getattr(record, attr_name, None)
    return str(value) if value else None


def _flatten_generated_files(value: object) -> Iterable[tuple[str | None, str]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(item, (list, tuple, set)):
                for nested in item:
                    if nested:
                        yield str(key), str(nested)
            elif item:
                yield str(key), str(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            if item:
                yield None, str(item)
    elif value:
        yield None, str(value)


def _existing_artifact_paths(workspace_id: str) -> set[str]:
    workspace = load_project_workspace(workspace_id)
    if workspace is None:
        return set()
    return {artifact.path for artifact in workspace.artifacts}


def _attach_unique_artifact(
    workspace_id: str,
    *,
    artifact_type: str,
    path: str | None,
    existing_paths: set[str],
    label: str | None = None,
    source_run_id: str | None = None,
) -> ProjectWorkspaceArtifact | None:
    if not path or path in existing_paths:
        return None
    artifact = attach_project_artifact(
        workspace_id,
        artifact_type=artifact_type,
        path=path,
        label=label,
        source_run_id=source_run_id,
    )
    existing_paths.add(path)
    return artifact


def sync_workflow_artifacts_to_project_workspace(
    workspace_id: str,
    result: WorkflowResult,
    *,
    source_run_id: str | None = None,
) -> dict[str, object]:
    """Attach local artifacts from a workflow result to a workspace."""
    if load_project_workspace(workspace_id) is None:
        raise KeyError(workspace_id)

    existing_paths = _existing_artifact_paths(workspace_id)
    attached: list[ProjectWorkspaceArtifact] = []
    skipped_count = 0

    for export in result.rule_export_results:
        artifact = _attach_unique_artifact(
            workspace_id,
            artifact_type="quality_rule_export",
            path=_path_from_record(export, "output_path"),
            existing_paths=existing_paths,
            label=_artifact_label("quality_rules", export.export_format, export.status),
            source_run_id=source_run_id,
        )
        attached.append(artifact) if artifact is not None else None
        skipped_count += artifact is None

    for export in result.execution_package_export_results:
        artifact = _attach_unique_artifact(
            workspace_id,
            artifact_type="execution_package",
            path=_path_from_record(export, "output_path"),
            existing_paths=existing_paths,
            label=_artifact_label(export.package_id, export.export_format, export.status),
            source_run_id=source_run_id,
        )
        attached.append(artifact) if artifact is not None else None
        skipped_count += artifact is None

    for workbook in result.confirmation_workbook_results:
        artifact = _attach_unique_artifact(
            workspace_id,
            artifact_type="confirmation_workbook",
            path=_path_from_record(workbook, "output_path"),
            existing_paths=existing_paths,
            label=_artifact_label(workbook.workbook_type, workbook.status),
            source_run_id=source_run_id,
        )
        attached.append(artifact) if artifact is not None else None
        skipped_count += artifact is None

    package = result.governance_delivery_package_result
    if package is not None:
        artifact = _attach_unique_artifact(
            workspace_id,
            artifact_type="delivery_package",
            path=package.output_dir,
            existing_paths=existing_paths,
            label=_artifact_label(package.package_name, package.status),
            source_run_id=source_run_id,
        )
        attached.append(artifact) if artifact is not None else None
        skipped_count += artifact is None
        for label, generated_path in _flatten_generated_files(package.generated_files):
            artifact = _attach_unique_artifact(
                workspace_id,
                artifact_type="delivery_artifact",
                path=generated_path,
                existing_paths=existing_paths,
                label=_artifact_label(label, Path(generated_path).name),
                source_run_id=source_run_id,
            )
            attached.append(artifact) if artifact is not None else None
            skipped_count += artifact is None

    return {
        "attached_artifact_count": len(attached),
        "skipped_artifact_count": skipped_count,
        "artifact_ids": [artifact.artifact_id for artifact in attached],
    }


def sync_workflow_reviews_to_project_workspace(
    workspace_id: str,
    result: WorkflowResult,
) -> dict[str, object]:
    """Sync review-like workflow summaries into workspace review queues."""
    if load_project_workspace(workspace_id) is None:
        raise KeyError(workspace_id)

    synced_queues: list[str] = []
    review_summary = result.review_summary
    if review_summary is not None:
        set_project_review_state(
            workspace_id,
            queue_name="manual_review",
            pending_count=review_summary.manual_review_count,
            accepted_count=review_summary.accepted_count,
            edited_count=review_summary.edited_count,
            rejected_count=review_summary.rejected_count,
        )
        synced_queues.append("manual_review")

    quality_queue = dict(result.quality_review_queue_summary or {})
    if quality_queue:
        set_project_review_state(
            workspace_id,
            queue_name="quality_rules",
            pending_count=int(quality_queue.get("low_confidence_rule_count") or 0),
        )
        synced_queues.append("quality_rules")

    if result.backlog_summary is not None:
        by_status: Mapping[str, Any] = result.backlog_summary.by_status
        completed_or_dropped = result.backlog_summary.completed_count + int(
            by_status.get("dropped") or 0
        )
        pending_count = max(0, result.backlog_summary.total_items - completed_or_dropped)
        set_project_review_state(
            workspace_id,
            queue_name="governance_backlog",
            pending_count=pending_count,
            accepted_count=result.backlog_summary.completed_count,
            needs_business_confirmation_count=result.backlog_summary.blocked_count,
        )
        synced_queues.append("governance_backlog")

    return {
        "synced_review_queue_count": len(synced_queues),
        "review_queues": synced_queues,
    }


def sync_workflow_result_to_project_workspace(
    workspace_id: str,
    result: WorkflowResult,
    *,
    workflow_profile: str = "metadata_governance_workflow",
    status: str | None = None,
    input_file_path: str | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    """Record a workflow run and sync its review queues and local artifacts."""
    if load_project_workspace(workspace_id) is None:
        raise KeyError(workspace_id)

    run = record_project_run(
        workspace_id,
        workflow_profile=workflow_profile,
        status=status or result.status or "success",
        input_file_path=input_file_path,
        result_summary=_workflow_summary(result),
        notes=notes,
    )
    review_result = sync_workflow_reviews_to_project_workspace(workspace_id, result)
    artifact_result = sync_workflow_artifacts_to_project_workspace(
        workspace_id,
        result,
        source_run_id=run.run_id,
    )
    summary = summarize_project_workspace(workspace_id)
    return {
        "run_id": run.run_id,
        **review_result,
        **artifact_result,
        "project_workspace_summary": summary.model_dump() if summary else None,
    }

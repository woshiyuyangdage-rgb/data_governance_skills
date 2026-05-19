"""Batch governance and snapshot tool handlers."""

from typing import Protocol

from app.core.governance.batch_snapshot_store import (
    list_batch_snapshots,
    load_latest_batch_snapshot,
)
from app.core.governance.incremental_diff_service import IncrementalDiffService
from app.core.models.tool_call_response import ToolCallResponse
from app.core.orchestrator.pipeline_service import (
    run_batch_governance_workflow_from_files,
)


class DeliveryBatchToolContext(Protocol):
    """Subset of executor helpers used by batch delivery tools."""

    def _optional_string(
        self, arguments: dict[str, object], name: str
    ) -> str | None: ...


def _batch_arguments(
    context: DeliveryBatchToolContext,
    arguments: dict[str, object],
) -> tuple[list[str], str, str | None]:
    file_paths = (
        [str(path) for path in arguments.get("file_paths", []) if str(path).strip()]
        if isinstance(arguments.get("file_paths"), list)
        else []
    )
    file_path = context._optional_string(arguments, "file_path")
    if file_path:
        file_paths.append(file_path)
    if not file_paths:
        raise ValueError("Argument 'file_paths' or 'file_path' is required.")
    group_by = context._optional_string(arguments, "group_by") or "system_name"
    batch_name = context._optional_string(
        arguments,
        "batch_name",
    ) or context._optional_string(
        arguments,
        "base_filename",
    )
    return file_paths, group_by, batch_name


class DeliveryBatchToolMixin:
    """Tool handlers for batch governance and snapshot comparison."""

    def _batch_arguments(
        self,
        arguments: dict[str, object],
    ) -> tuple[list[str], str, str | None]:
        return _batch_arguments(self, arguments)

    def run_batch_governance(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run multi-file batch governance."""
        tool_name = "run_batch_governance"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=False,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=(
                    rerun_scope.get("rerun_object_count") if rerun_scope else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run batch governance: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run batch governance.",
                None,
                trace,
            )

    def run_incremental_rerun(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run changed-only batch governance using local snapshots."""
        tool_name = "run_incremental_rerun"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_paths, group_by, batch_name = self._batch_arguments(arguments)
            result = run_batch_governance_workflow_from_files(
                file_paths,
                group_by=group_by,
                changed_only=True,
                batch_name=batch_name,
            )
            summary = result.incremental_diff_summary
            rerun_scope = result.rerun_scope_summary
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                batch_name=rerun_scope.get("batch_name") if rerun_scope else batch_name,
                file_count=len(file_paths),
                group_count=len(result.batch_group_results),
                changed_count=summary.changed_count if summary else None,
                new_count=summary.new_count if summary else None,
                unchanged_count=summary.unchanged_count if summary else None,
                removed_count=summary.removed_count if summary else None,
                rerun_object_count=(
                    rerun_scope.get("rerun_object_count") if rerun_scope else None
                ),
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run incremental rerun: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run incremental rerun.",
                None,
                trace,
            )

    def compare_governance_snapshots(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Compare latest stored snapshot metadata."""
        tool_name = "compare_governance_snapshots"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            batch_name = (
                self._optional_string(arguments, "batch_name")
                or "default_batch_governance"
            )
            latest = load_latest_batch_snapshot(batch_name)
            snapshots = list_batch_snapshots(batch_name)
            fingerprints = latest.get("fingerprints", []) if latest else []
            diff_items = IncrementalDiffService().compare_fingerprints(
                fingerprints,
                fingerprints,
            )
            summary = IncrementalDiffService.build_incremental_diff_summary(diff_items)
            latest_payload = None
            if latest:
                latest_payload = dict(latest)
                latest_payload["fingerprints"] = [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in fingerprints
                ]
            result = {
                "batch_name": batch_name,
                "latest_snapshot": latest_payload,
                "snapshots": snapshots,
                "incremental_diff_items": [
                    item.model_dump() for item in diff_items
                ],
                "incremental_diff_summary": summary.model_dump(),
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Governance snapshots were compared successfully.",
                batch_name=batch_name,
                changed_count=summary.changed_count,
                new_count=summary.new_count,
                unchanged_count=summary.unchanged_count,
                removed_count=summary.removed_count,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance snapshots were compared successfully.",
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to compare governance snapshots: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to compare governance snapshots.",
                None,
                trace,
            )

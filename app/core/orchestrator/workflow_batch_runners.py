"""Batch workflow runner helpers."""

from app.core.delivery.delivery_service import DeliveryService
from app.core.governance.batch_snapshot_store import (
    load_latest_batch_snapshot,
    save_batch_snapshot,
)
from app.core.governance.fingerprint_builder import FingerprintBuilder
from app.core.governance.incremental_diff_service import IncrementalDiffService
from app.core.models.batch_group_result import BatchGroupResult
from app.core.models.batch_run_result import BatchRunResult
from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.parser.batch_loader import group_tables_by_field, load_metadata_files


class WorkflowBatchRunnerMixin:
    """Run multi-file batch governance workflows."""

    @staticmethod
    def _batch_object_name(table: TableMeta) -> str:
        return ".".join(
            part
            for part in [table.system_name, table.schema_name, table.table_name]
            if part
        ) or table.table_name

    def _select_tables_for_rerun(
        self,
        grouped_tables: dict[str, list[TableMeta]],
        rerun_object_names: set[str],
        changed_only: bool,
    ) -> dict[str, list[TableMeta]]:
        if not changed_only:
            return grouped_tables
        selected: dict[str, list[TableMeta]] = {}
        for group_name, tables in grouped_tables.items():
            scoped_tables = [
                table
                for table in tables
                if self._batch_object_name(table) in rerun_object_names
            ]
            if scoped_tables:
                selected[group_name] = scoped_tables
        return selected

    def run_batch_governance_workflow(
        self,
        file_paths: list[str],
        group_by: str = "system_name",
        changed_only: bool = False,
        batch_name: str | None = None,
    ) -> WorkflowResult:
        """Run multi-file governance processing with optional changed-only scope."""
        resolved_batch_name = batch_name or "default_batch_governance"
        tables = load_metadata_files(file_paths)
        grouped_tables = group_tables_by_field(tables, group_by=group_by)
        fingerprint_builder = FingerprintBuilder()
        fingerprints = fingerprint_builder.build_grouped_fingerprints(grouped_tables)
        previous_snapshot = load_latest_batch_snapshot(resolved_batch_name)
        old_fingerprints = (
            previous_snapshot.get("fingerprints", []) if previous_snapshot else []
        )
        diff_service = IncrementalDiffService()
        diff_items = diff_service.compare_fingerprints(old_fingerprints, fingerprints)
        diff_summary = diff_service.build_incremental_diff_summary(diff_items)
        rerun_items = (
            diff_service.filter_changed_objects(diff_items) if changed_only else diff_items
        )
        rerun_object_names = {item.object_name for item in rerun_items}
        selected_groups = self._select_tables_for_rerun(
            grouped_tables,
            rerun_object_names,
            changed_only=changed_only,
        )

        group_results: list[BatchGroupResult] = []
        for group_name, group_tables in selected_groups.items():
            group_result = self.run_governance_backlog_build(
                group_tables,
                apply_review=True,
            )
            group_results.append(
                BatchGroupResult(
                    group_name=group_name,
                    file_count=len(file_paths),
                    table_count=len(group_tables),
                    status=group_result.status,
                    summary=group_result.message,
                )
            )

        snapshot_path = save_batch_snapshot(
            resolved_batch_name,
            fingerprints,
            metadata={
                "file_paths": file_paths,
                "group_by": group_by,
                "changed_only": changed_only,
            },
        )
        rerun_scope_summary = {
            "batch_name": resolved_batch_name,
            "file_count": len(file_paths),
            "group_count": len(grouped_tables),
            "selected_group_count": len(selected_groups),
            "rerun_object_count": len(rerun_object_names) if changed_only else len(tables),
            "changed_only": changed_only,
            "snapshot_path": snapshot_path,
        }
        batch_run_result = BatchRunResult(
            batch_name=resolved_batch_name,
            group_results=group_results,
            diff_summary=diff_summary,
            status="success",
            message=(
                f"Batch governance run completed for {len(file_paths)} files "
                f"and {len(grouped_tables)} groups."
            ),
        )
        return WorkflowResult(
            input_table_count=len(tables),
            status="success",
            message=batch_run_result.message or "",
            batch_run_result=batch_run_result,
            batch_group_results=group_results,
            incremental_diff_items=diff_items,
            incremental_diff_summary=diff_summary,
            rerun_scope_summary=rerun_scope_summary,
            skill_outputs={
                "batch_processing_output": {
                    "batch_run_result": batch_run_result.model_dump(),
                    "rerun_scope_summary": rerun_scope_summary,
                }
            },
        )

    def run_batch_governance_delivery(
        self,
        file_paths: list[str],
        group_by: str = "system_name",
        changed_only: bool = False,
        batch_name: str | None = None,
    ) -> WorkflowResult:
        """Run batch governance and attach a batch-level delivery package."""
        result = self.run_batch_governance_workflow(
            file_paths=file_paths,
            group_by=group_by,
            changed_only=changed_only,
            batch_name=batch_name or "batch_delivery_package",
        )
        return DeliveryService().build_governance_delivery_package(
            result,
            base_name=batch_name or "batch_delivery_package",
        )

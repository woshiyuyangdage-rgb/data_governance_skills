"""Markdown report operational section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_delivery_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Governance Delivery Package", ""]
    if result.confirmation_workbook_results:
        lines.append(
            f"- Confirmation workbook count: {len(result.confirmation_workbook_results)}"
        )
        for workbook in result.confirmation_workbook_results:
            lines.append(
                f"- {workbook.workbook_type} | rows={workbook.row_count} | path=`{workbook.output_path}`"
            )
    else:
        lines.append("- No confirmation workbooks available.")
    if result.governance_delivery_package_result is not None:
        package_result = result.governance_delivery_package_result
        lines.append(f"- Delivery package: `{package_result.package_name}`")
        lines.append(f"- Output dir: `{package_result.output_dir}`")
        lines.append(f"- Generated files: {len(package_result.generated_files)}")
    if result.governance_delivery_manifest is not None:
        manifest = result.governance_delivery_manifest
        lines.append(
            f"- Manifest artifacts: {len(manifest.included_artifacts)} | generated_at={manifest.generated_at or 'N/A'}"
        )
    return lines


def build_batch_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Batch Processing Summary", ""]
    if result.batch_group_results:
        lines.append(f"- Batch groups: {len(result.batch_group_results)}")
        for group in result.batch_group_results:
            lines.append(
                f"- `{group.group_name}` | files={group.file_count} | tables={group.table_count} | status={group.status}"
            )
    else:
        lines.append("- No batch group results available.")

    lines.extend(["", "# Incremental Diff Summary", ""])
    if result.incremental_diff_summary is not None:
        summary = result.incremental_diff_summary
        lines.append(f"- Total objects: {summary.total_objects}")
        lines.append(f"- New: {summary.new_count}")
        lines.append(f"- Changed: {summary.changed_count}")
        lines.append(f"- Unchanged: {summary.unchanged_count}")
        lines.append(f"- Removed: {summary.removed_count}")
        lines.append(f"- Pending review: {summary.pending_review_count}")
        lines.append(f"- Summary: {summary.summary or 'N/A'}")
    else:
        lines.append("- No incremental diff summary available.")

    lines.extend(["", "# Rerun Scope Summary", ""])
    if result.rerun_scope_summary:
        for key, value in result.rerun_scope_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No rerun scope summary available.")
    return lines


def build_workbook_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Workbook Import Summary", ""]
    if result.workbook_import_summaries:
        for summary in result.workbook_import_summaries:
            lines.append(
                f"- {summary.workbook_type} | imported={summary.imported_count} | "
                f"skipped={summary.skipped_count} | invalid={summary.invalid_count}"
            )
    else:
        lines.append("- No workbook import summaries available.")

    lines.extend(["", "# Confirmation Round-Trip Results", ""])
    if result.roundtrip_results:
        for roundtrip in result.roundtrip_results:
            lines.append(
                f"- {roundtrip.workbook_type} | status={roundtrip.status} | "
                f"review_records={roundtrip.generated_review_records_count} | "
                f"backlog_updates={roundtrip.generated_backlog_updates_count} | "
                f"changed_objects={len(roundtrip.changed_object_keys)}"
            )
        if result.roundtrip_changed_objects_summary:
            lines.append(
                f"- Changed object count: {result.roundtrip_changed_objects_summary.get('changed_object_count', 0)}"
            )
    else:
        lines.append("- No confirmation round-trip results available.")
    return lines


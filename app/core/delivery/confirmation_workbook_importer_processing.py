"""Import orchestration helpers for confirmation workbook imports."""

from typing import Any

import pandas as pd

from app.core.delivery.confirmation_template_loader import (
    get_confirmation_template_profile,
)
from app.core.delivery.confirmation_workbook_importer_constants import REQUIRED_COLUMNS
from app.core.delivery.confirmation_workbook_importer_payload import (
    WorkbookImportPayload,
)
from app.core.delivery.confirmation_workbook_importer_template import (
    build_match_result_for_template,
    build_template_mapping_result,
    dataframe_from_template_mapping,
    diagnose_confirmation_template,
)
from app.core.models.confirmation_template_mapping_result import (
    ConfirmationTemplateMappingResult,
)
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.workbook_import_row_result import WorkbookImportRowResult
from app.core.models.workbook_import_summary import WorkbookImportSummary
from app.core.models.workbook_validation_result import WorkbookValidationResult


def clean_value(value: object) -> object | None:
    """Normalize one imported cell value."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def build_row_object_key(workbook_type: str, row: dict[str, Any]) -> str | None:
    """Build a stable object key from one normalized workbook row."""
    if workbook_type == "backlog_confirmation":
        return str(row.get("backlog_id") or "").strip() or None
    table = str(row.get("source_table_name") or "").strip()
    field_name = str(row.get("source_field_name") or "").strip()
    if workbook_type == "quality_rule_confirmation":
        rule_type = str(row.get("rule_type") or "").strip()
        return ".".join(part for part in [table, field_name, rule_type] if part) or None
    return ".".join(part for part in [table, field_name] if part) or None


def summarize_import_results(
    workbook_type: str,
    row_results: list[WorkbookImportRowResult],
    normalized_rows: list[dict[str, Any]],
) -> WorkbookImportSummary:
    """Build import count summary."""
    action_counts = {"accept": 0, "reject": 0, "edit": 0, "mark_for_manual_review": 0}
    for row in normalized_rows:
        action = str(row.get("confirmation_status") or "")
        if action in action_counts:
            action_counts[action] += 1
    imported_count = sum(1 for row in row_results if row.status == "imported")
    skipped_count = sum(1 for row in row_results if row.status == "skipped")
    invalid_count = sum(1 for row in row_results if row.status == "invalid")
    return WorkbookImportSummary(
        workbook_type=workbook_type,
        total_rows=len(row_results),
        imported_count=imported_count,
        skipped_count=skipped_count,
        invalid_count=invalid_count,
        accepted_count=action_counts["accept"],
        rejected_count=action_counts["reject"],
        edited_count=action_counts["edit"],
        manual_review_count=action_counts["mark_for_manual_review"],
        summary=(
            f"{imported_count} imported, {skipped_count} skipped, "
            f"{invalid_count} invalid."
        ),
    )


def _failed_import_payload(
    workbook_type: str,
    validation: WorkbookValidationResult,
    summary_message: str,
    template_match: ConfirmationTemplateMatchResult | None = None,
    template_mapping: ConfirmationTemplateMappingResult | None = None,
) -> WorkbookImportPayload:
    """Build a zero-row payload for a failed import path."""
    return WorkbookImportPayload(
        workbook_type=workbook_type,
        validation_result=validation,
        import_summary=WorkbookImportSummary(
            workbook_type=workbook_type,
            total_rows=0,
            imported_count=0,
            skipped_count=0,
            invalid_count=0,
            accepted_count=0,
            rejected_count=0,
            edited_count=0,
            manual_review_count=0,
            summary=summary_message,
        ),
        row_results=[],
        normalized_rows=[],
        confirmation_template_match_result=template_match,
        confirmation_template_mapping_result=template_mapping,
    )


def import_normalized_dataframe(
    importer,
    dataframe: pd.DataFrame,
    workbook_type: str,
    validation: WorkbookValidationResult,
    template_match: ConfirmationTemplateMatchResult | None = None,
    template_mapping: ConfirmationTemplateMappingResult | None = None,
) -> WorkbookImportPayload:
    """Import one already-normalized confirmation dataframe."""
    if not validation.is_valid:
        return _failed_import_payload(
            workbook_type,
            validation,
            "Workbook validation failed.",
            template_match=template_match,
            template_mapping=template_mapping,
        )

    dataframe = dataframe.where(pd.notna(dataframe), None)
    policy = importer.policies.get("import_policy", {})
    row_results: list[WorkbookImportRowResult] = []
    normalized_rows: list[dict[str, Any]] = []
    required = REQUIRED_COLUMNS.get(workbook_type, [])

    for index, raw_row in enumerate(dataframe.to_dict("records"), start=2):
        row = dict(raw_row)
        if bool(policy.get("skip_empty_rows", True)) and not any(
            str(value or "").strip() for value in row.values()
        ):
            row_results.append(
                WorkbookImportRowResult(
                    workbook_type=workbook_type,
                    row_index=index,
                    status="skipped",
                    message="Empty row skipped.",
                )
            )
            continue
        missing_values = [
            column for column in required if not str(row.get(column) or "").strip()
        ]
        object_key = build_row_object_key(workbook_type, row)
        if missing_values:
            row_results.append(
                WorkbookImportRowResult(
                    workbook_type=workbook_type,
                    row_index=index,
                    object_key=object_key,
                    status="invalid",
                    message=f"Missing required values: {', '.join(missing_values)}",
                )
            )
            continue
        normalized_status = importer.normalize_confirmation_status(row.get("confirmation_status"))
        if workbook_type == "backlog_confirmation" and normalized_status is None:
            normalized_status = str(row.get("confirmation_status") or "").strip()
        if normalized_status is None:
            row_results.append(
                WorkbookImportRowResult(
                    workbook_type=workbook_type,
                    row_index=index,
                    object_key=object_key,
                    status="invalid",
                    message="Unknown confirmation_status.",
                )
            )
            continue
        if normalized_status == "pending":
            row_results.append(
                WorkbookImportRowResult(
                    workbook_type=workbook_type,
                    row_index=index,
                    object_key=object_key,
                    status="skipped",
                    message="Pending row skipped.",
                )
            )
            continue
        row["confirmation_status"] = normalized_status
        row["reviewer_note"] = row.get("reviewer_note") or ""
        row["object_key"] = object_key
        normalized_rows.append(row)
        row_results.append(
            WorkbookImportRowResult(
                workbook_type=workbook_type,
                row_index=index,
                object_key=object_key,
                status="imported",
                message="Row imported.",
            )
        )

    summary = summarize_import_results(workbook_type, row_results, normalized_rows)
    return WorkbookImportPayload(
        workbook_type=workbook_type,
        validation_result=validation,
        import_summary=summary,
        row_results=row_results,
        normalized_rows=normalized_rows,
        confirmation_template_match_result=template_match,
        confirmation_template_mapping_result=template_mapping,
    )


def import_workbook(
    importer,
    file_path: str,
    workbook_type: str,
) -> WorkbookImportPayload:
    """Import one confirmation workbook and return normalized rows."""
    validation = importer.validate_workbook(file_path, workbook_type)
    dataframe = pd.DataFrame()
    if validation.is_valid:
        dataframe = importer._read_dataframe(file_path, sheet_name=validation.detected_sheet_name)
        dataframe = importer.normalize_columns(dataframe)
    return import_normalized_dataframe(importer, dataframe, workbook_type, validation)


def import_confirmation_with_template(
    importer,
    file_path: str,
    template_name: str | None = None,
    workbook_type: str | None = None,
    sheet_name: str | None = None,
) -> WorkbookImportPayload:
    """Import a confirmation workbook using template-specific column mapping."""
    match_result = None
    selected_template = template_name
    selected_sheet = sheet_name
    if selected_template is None:
        match_result = diagnose_confirmation_template(
            file_path,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        selected_template = match_result.matched_template_name
        selected_sheet = match_result.matched_sheet_name or sheet_name
    else:
        match_result = build_match_result_for_template(
            file_path,
            selected_template,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )
        selected_sheet = sheet_name or match_result.matched_sheet_name
    if selected_template is None:
        validation = WorkbookValidationResult(
            workbook_type=workbook_type or "unknown",
            is_valid=False,
            messages=["No confirmation workbook template was selected or matched."],
        )
        return _failed_import_payload(
            workbook_type or "unknown",
            validation,
            "Template matching failed.",
            template_match=match_result,
        )
    profile = get_confirmation_template_profile(selected_template)
    dataframe = importer._read_dataframe(file_path, sheet_name=selected_sheet)
    mapping_result = build_template_mapping_result(dataframe, selected_template)
    validation = WorkbookValidationResult(
        workbook_type=profile.workbook_type,
        is_valid=mapping_result.status == "success",
        detected_sheet_name=selected_sheet,
        required_columns_present=[
            field for field in profile.required_target_fields if field in mapping_result.mapped_fields
        ],
        missing_required_columns=list(mapping_result.missing_required_fields),
        messages=(
            []
            if mapping_result.status == "success"
            else [mapping_result.message or "Template mapping failed."]
        ),
    )
    normalized_dataframe = dataframe_from_template_mapping(
        dataframe,
        mapping_result,
        importer._clean_value,
    )
    return import_normalized_dataframe(
        importer,
        normalized_dataframe,
        profile.workbook_type,
        validation,
        template_match=match_result,
        template_mapping=mapping_result,
    )

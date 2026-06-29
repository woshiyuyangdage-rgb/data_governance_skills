"""Template diagnosis and column mapping helpers for confirmation imports."""

from collections.abc import Callable
from typing import Any

import pandas as pd

from app.core.delivery.confirmation_template_loader import (
    get_confirmation_template_profile,
    load_confirmation_template_mapping_specs,
)
from app.core.delivery.confirmation_template_matcher import ConfirmationTemplateMatcher
from app.core.delivery.confirmation_workbook_importer_constants import REQUIRED_COLUMNS
from app.core.models.confirmation_template_mapping_result import (
    ConfirmationTemplateMappingResult,
)
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)


def normalize_template_header(value: object) -> str:
    """Normalize one source or target header for template comparison."""
    return str(value or "").strip().replace(" ", "").replace("_", "").lower()


def diagnose_confirmation_template(
    file_path: str,
    workbook_type: str | None = None,
    sheet_name: str | None = None,
) -> ConfirmationTemplateMatchResult:
    """Diagnose confirmation workbook template from headers."""
    return ConfirmationTemplateMatcher().match(
        file_path,
        workbook_type=workbook_type,
        sheet_name=sheet_name,
    )


def build_template_mapping_result(
    dataframe: pd.DataFrame,
    template_name: str,
) -> ConfirmationTemplateMappingResult:
    """Map source columns to target confirmation fields using a template spec."""
    profile = get_confirmation_template_profile(template_name)
    spec = load_confirmation_template_mapping_specs().get(profile.mapping_spec_name)
    if spec is None:
        raise ValueError(f"Mapping spec '{profile.mapping_spec_name}' was not found.")
    source_columns = [str(column).strip() for column in dataframe.columns]
    normalized_source = {
        normalize_template_header(column): column for column in source_columns
    }
    target_fields = list(profile.required_target_fields) + list(profile.optional_target_fields)
    mapped_fields: dict[str, str] = {}
    for target_field in target_fields:
        aliases = [target_field] + list(spec.get(target_field, []))
        for alias in aliases:
            normalized_alias = normalize_template_header(alias)
            if normalized_alias in normalized_source:
                mapped_fields[target_field] = normalized_source[normalized_alias]
                break
    mapped_source = set(mapped_fields.values())
    missing_required = [
        field for field in profile.required_target_fields if field not in mapped_fields
    ]
    unmapped = [column for column in source_columns if column not in mapped_source]
    status = "success" if not missing_required else "failed"
    return ConfirmationTemplateMappingResult(
        template_name=profile.template_name,
        workbook_type=profile.workbook_type,
        source_columns=source_columns,
        mapped_fields=mapped_fields,
        unmapped_source_columns=unmapped,
        missing_required_fields=missing_required,
        status=status,
        message=(
            "Confirmation workbook columns mapped to target fields."
            if status == "success"
            else "Required target fields are missing: " + ", ".join(missing_required)
        ),
    )


def dataframe_from_template_mapping(
    dataframe: pd.DataFrame,
    mapping_result: ConfirmationTemplateMappingResult,
    clean_value: Callable[[object], object | None],
    required_columns: dict[str, list[str]] = REQUIRED_COLUMNS,
) -> pd.DataFrame:
    """Build a canonical confirmation dataframe from template mapping."""
    rows: list[dict[str, Any]] = []
    target_fields = set(mapping_result.mapped_fields.keys()).union(
        set(required_columns.get(mapping_result.workbook_type, []))
    )
    for raw_row in dataframe.to_dict("records"):
        row: dict[str, Any] = {}
        for target_field in target_fields:
            source_column = mapping_result.mapped_fields.get(target_field)
            row[target_field] = clean_value(raw_row.get(source_column)) if source_column else None
        rows.append(row)
    return pd.DataFrame(rows)


def build_match_result_for_template(
    file_path: str,
    template_name: str,
    workbook_type: str | None = None,
    sheet_name: str | None = None,
) -> ConfirmationTemplateMatchResult:
    """Diagnose the best sheet for an explicitly selected template profile."""
    profile = get_confirmation_template_profile(template_name)
    matcher = ConfirmationTemplateMatcher()
    sheet_headers = matcher.read_candidate_sheet_headers(file_path, sheet_name=sheet_name)
    best_sheet: str | None = None
    best_score: dict[str, Any] | None = None
    for candidate_sheet, headers in sheet_headers.items():
        score = matcher.score_template_profile(
            profile,
            headers,
            workbook_type=workbook_type or profile.workbook_type,
        )
        if best_score is None or (score["confidence"], score["score"]) > (
            best_score["confidence"],
            best_score["score"],
        ):
            best_sheet = candidate_sheet
            best_score = score
    if best_score is None:
        return ConfirmationTemplateMatchResult(
            matched_template_name=profile.template_name,
            workbook_type=profile.workbook_type,
            confidence=0.0,
            fallback_used=True,
            message="No readable confirmation workbook sheet matched the selected template.",
        )
    missing_required = list(best_score["missing_required_fields"])
    warnings: list[str] = []
    if missing_required:
        warnings.append("Missing required fields: " + ", ".join(missing_required))
    if workbook_type and workbook_type != profile.workbook_type:
        warnings.append(
            f"Selected template workbook type '{profile.workbook_type}' differs from requested '{workbook_type}'."
        )
    return ConfirmationTemplateMatchResult(
        matched_template_name=profile.template_name,
        workbook_type=profile.workbook_type,
        confidence=float(best_score["confidence"]),
        matched_sheet_name=best_sheet,
        matched_headers=list(best_score["matched_headers"]),
        missing_required_fields=missing_required,
        unmapped_source_columns=list(best_score["unmapped_source_columns"]),
        fallback_used=bool(missing_required),
        warnings=warnings,
        message=(
            f"Selected confirmation template '{profile.template_name}' was applied."
            if not missing_required
            else "Selected confirmation template was applied, but required fields are missing."
        ),
    )

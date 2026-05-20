"""Validation and normalization helpers for confirmation workbook imports."""

from pathlib import Path

import pandas as pd

from app.core.delivery.confirmation_workbook_importer_constants import REQUIRED_COLUMNS
from app.core.models.workbook_validation_result import WorkbookValidationResult


def detect_main_sheet(
    file_path: str,
    workbook_type: str,
    policies: dict[str, object],
) -> str:
    """Detect the main workbook sheet from configured candidates."""
    path = Path(file_path)
    if path.suffix.lower() == ".csv":
        return ""
    excel = pd.ExcelFile(file_path)
    sheet_lookup = {sheet.lower(): sheet for sheet in excel.sheet_names}
    workbook_config = policies.get("workbook_types", {}).get(workbook_type, {})
    candidates = workbook_config.get("main_sheet_candidates", [])
    for candidate in candidates:
        if str(candidate).lower() in sheet_lookup:
            return sheet_lookup[str(candidate).lower()]
    if bool(policies.get("import_policy", {}).get("default_sheet_name_fallback", True)):
        return excel.sheet_names[-1]
    raise ValueError(f"No supported sheet was found for workbook type '{workbook_type}'.")


def read_dataframe(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Read a confirmation workbook into a DataFrame."""
    path = Path(file_path)
    extension = path.suffix.lower()
    if extension == ".csv":
        return pd.read_csv(path)
    if extension in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name or 0)
    raise ValueError(f"Unsupported confirmation workbook file type '{extension or '<none>'}'.")

def _normalize_column_name(value: object) -> str:
    return str(value or "").strip().lower()


def normalize_columns(dataframe: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    """Normalize configured column aliases to canonical column names."""
    alias_lookup: dict[str, str] = {}
    for canonical, alias_values in aliases.items():
        alias_lookup[_normalize_column_name(canonical)] = canonical
        for alias in alias_values or []:
            alias_lookup[_normalize_column_name(alias)] = canonical
    renamed: dict[object, str] = {}
    for column in dataframe.columns:
        normalized = _normalize_column_name(column)
        renamed[column] = alias_lookup.get(normalized, normalized)
    return dataframe.rename(columns=renamed)


def normalize_confirmation_status(
    status: object,
    policies: dict[str, object],
) -> str | None:
    """Normalize reviewer status to local review action values."""
    text = str(status or "").strip().lower()
    if not text:
        return None
    mapping = policies.get("confirmation_status_mapping", {})
    return mapping.get(text)


def validate_workbook(
    file_path: str,
    workbook_type: str,
    policies: dict[str, object],
    aliases: dict[str, list[str]],
) -> WorkbookValidationResult:
    """Validate workbook sheet and required columns."""
    messages: list[str] = []
    warnings: list[str] = []
    try:
        path = Path(file_path)
        sheet_name = (
            None
            if path.suffix.lower() == ".csv"
            else detect_main_sheet(file_path, workbook_type, policies)
        )
        dataframe = read_dataframe(file_path, sheet_name=sheet_name)
        dataframe = normalize_columns(dataframe, aliases)
    except Exception as exc:
        return WorkbookValidationResult(
            workbook_type=workbook_type,
            is_valid=False,
            messages=[f"Failed to read workbook: {exc}"],
        )
    required = REQUIRED_COLUMNS.get(workbook_type, [])
    present = [column for column in required if column in dataframe.columns]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        messages.append(f"Missing required columns: {', '.join(missing)}")
    if dataframe.empty:
        warnings.append("Workbook main sheet is empty.")
    return WorkbookValidationResult(
        workbook_type=workbook_type,
        is_valid=not missing,
        detected_sheet_name=sheet_name,
        required_columns_present=present,
        missing_required_columns=missing,
        warnings=warnings,
        messages=messages,
    )

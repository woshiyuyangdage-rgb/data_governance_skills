"""Import and validate confirmation workbooks."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.delivery.confirmation_workbook_importer_constants import REQUIRED_COLUMNS
from app.core.delivery.confirmation_workbook_importer_payload import (
    WorkbookImportPayload,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    build_row_object_key as _build_row_object_key,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    clean_value as _clean_value,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    import_confirmation_with_template as _import_confirmation_with_template,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    import_normalized_dataframe as _import_normalized_dataframe,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    import_workbook as _import_workbook,
)
from app.core.delivery.confirmation_workbook_importer_processing import (
    summarize_import_results as _summarize_import_results,
)
from app.core.delivery.confirmation_workbook_importer_template import (
    build_match_result_for_template as _build_match_result_for_template,
)
from app.core.delivery.confirmation_workbook_importer_template import (
    build_template_mapping_result as _build_template_mapping_result,
)
from app.core.delivery.confirmation_workbook_importer_template import (
    dataframe_from_template_mapping as _dataframe_from_template_mapping,
)
from app.core.delivery.confirmation_workbook_importer_template import (
    diagnose_confirmation_template as _diagnose_confirmation_template,
)
from app.core.delivery.confirmation_workbook_importer_validation import (
    detect_main_sheet as _detect_main_sheet,
)
from app.core.delivery.confirmation_workbook_importer_validation import (
    normalize_columns as _normalize_columns,
)
from app.core.delivery.confirmation_workbook_importer_validation import (
    normalize_confirmation_status as _normalize_confirmation_status,
)
from app.core.delivery.confirmation_workbook_importer_validation import (
    read_dataframe as _read_dataframe,
)
from app.core.delivery.confirmation_workbook_importer_validation import (
    validate_workbook as _validate_workbook,
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
from app.core.rules.config_loader import (
    get_workbook_column_aliases_config,
    get_workbook_import_policies_config,
)


class ConfirmationWorkbookImporter:
    """Validate and import round-trip confirmation workbooks."""

    def __init__(self) -> None:
        self.policies = get_workbook_import_policies_config()
        self.aliases = get_workbook_column_aliases_config().get("aliases", {})

    def detect_main_sheet(self, file_path: str, workbook_type: str) -> str:
        """Detect the main workbook sheet from configured candidates."""
        return _detect_main_sheet(file_path, workbook_type, self.policies)

    @staticmethod
    def _normalize_column_name(value: object) -> str:
        return str(value or "").strip().lower()

    def normalize_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Normalize configured column aliases to canonical column names."""
        return _normalize_columns(dataframe, self.aliases)

    def normalize_confirmation_status(self, status: object) -> str | None:
        """Normalize reviewer status to local review action values."""
        return _normalize_confirmation_status(status, self.policies)

    @staticmethod
    def _read_dataframe(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
        return _read_dataframe(file_path, sheet_name=sheet_name)

    @staticmethod
    def _clean_value(value: object) -> object | None:
        return _clean_value(value)

    def diagnose_confirmation_template(
        self,
        file_path: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> ConfirmationTemplateMatchResult:
        """Diagnose confirmation workbook template from headers."""
        return _diagnose_confirmation_template(
            file_path,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )

    def build_template_mapping_result(
        self,
        dataframe: pd.DataFrame,
        template_name: str,
    ) -> ConfirmationTemplateMappingResult:
        """Map source columns to target confirmation fields using a template spec."""
        return _build_template_mapping_result(dataframe, template_name)

    def dataframe_from_template_mapping(
        self,
        dataframe: pd.DataFrame,
        mapping_result: ConfirmationTemplateMappingResult,
    ) -> pd.DataFrame:
        """Build a canonical confirmation dataframe from template mapping."""
        return _dataframe_from_template_mapping(dataframe, mapping_result, self._clean_value)

    def validate_workbook(
        self,
        file_path: str,
        workbook_type: str,
    ) -> WorkbookValidationResult:
        """Validate workbook sheet and required columns."""
        return _validate_workbook(file_path, workbook_type, self.policies, self.aliases)

    @staticmethod
    def build_row_object_key(workbook_type: str, row: dict[str, Any]) -> str | None:
        """Build a stable object key from one normalized workbook row."""
        return _build_row_object_key(workbook_type, row)

    def summarize_import_results(
        self,
        workbook_type: str,
        row_results: list[WorkbookImportRowResult],
        normalized_rows: list[dict[str, Any]],
    ) -> WorkbookImportSummary:
        """Build import count summary."""
        return _summarize_import_results(workbook_type, row_results, normalized_rows)

    def _import_normalized_dataframe(
        self,
        dataframe: pd.DataFrame,
        workbook_type: str,
        validation: WorkbookValidationResult,
        template_match: ConfirmationTemplateMatchResult | None = None,
        template_mapping: ConfirmationTemplateMappingResult | None = None,
    ) -> WorkbookImportPayload:
        """Import one already-normalized confirmation dataframe."""
        return _import_normalized_dataframe(
            self,
            dataframe,
            workbook_type,
            validation,
            template_match=template_match,
            template_mapping=template_mapping,
        )

    def import_workbook(self, file_path: str, workbook_type: str) -> WorkbookImportPayload:
        """Import one confirmation workbook and return normalized rows."""
        return _import_workbook(self, file_path, workbook_type)

    def build_match_result_for_template(
        self,
        file_path: str,
        template_name: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> ConfirmationTemplateMatchResult:
        """Diagnose the best sheet for an explicitly selected template profile."""
        return _build_match_result_for_template(
            file_path,
            template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )

    def import_confirmation_with_template(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkbookImportPayload:
        """Import a confirmation workbook using template-specific column mapping."""
        return _import_confirmation_with_template(
            self,
            file_path,
            template_name=template_name,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )

    def import_mapping_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "mapping_confirmation")

    def import_stg_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "stg_confirmation")

    def import_quality_rule_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "quality_rule_confirmation")

    def import_backlog_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "backlog_confirmation")


__all__ = [
    "ConfirmationWorkbookImporter",
    "REQUIRED_COLUMNS",
    "WorkbookImportPayload",
]

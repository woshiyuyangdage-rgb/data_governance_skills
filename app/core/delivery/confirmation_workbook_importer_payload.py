"""Structured payload returned by workbook importer."""

from dataclasses import dataclass, field
from typing import Any

from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.confirmation_template_mapping_result import (
    ConfirmationTemplateMappingResult,
)
from app.core.models.workbook_import_row_result import WorkbookImportRowResult
from app.core.models.workbook_import_summary import WorkbookImportSummary
from app.core.models.workbook_validation_result import WorkbookValidationResult


@dataclass
class WorkbookImportPayload:
    """Structured payload returned by workbook importer."""

    workbook_type: str
    validation_result: WorkbookValidationResult
    import_summary: WorkbookImportSummary
    row_results: list[WorkbookImportRowResult] = field(default_factory=list)
    normalized_rows: list[dict[str, Any]] = field(default_factory=list)
    confirmation_template_match_result: ConfirmationTemplateMatchResult | None = None
    confirmation_template_mapping_result: ConfirmationTemplateMappingResult | None = None

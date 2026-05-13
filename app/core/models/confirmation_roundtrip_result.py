"""Result model for confirmation workbook round-trip merge."""

from pydantic import BaseModel, Field

from app.core.models.workbook_import_summary import WorkbookImportSummary


class ConfirmationRoundTripResult(BaseModel):
    """Result of applying imported confirmation workbook rows."""

    workbook_type: str
    import_summary: WorkbookImportSummary
    generated_review_records_count: int = 0
    generated_override_updates_count: int = 0
    generated_backlog_updates_count: int = 0
    changed_object_keys: list[str] = Field(default_factory=list)
    status: str
    message: str | None = None


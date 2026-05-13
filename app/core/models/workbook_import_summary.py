"""Summary model for workbook imports."""

from pydantic import BaseModel


class WorkbookImportSummary(BaseModel):
    """Aggregated counts from one confirmation workbook import."""

    workbook_type: str
    total_rows: int
    imported_count: int
    skipped_count: int
    invalid_count: int
    accepted_count: int
    rejected_count: int
    edited_count: int
    manual_review_count: int
    summary: str | None = None


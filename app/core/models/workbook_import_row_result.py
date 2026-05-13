"""Row-level result for workbook imports."""

from pydantic import BaseModel


class WorkbookImportRowResult(BaseModel):
    """Validation/import status for one workbook row."""

    workbook_type: str
    row_index: int
    object_key: str | None = None
    status: str
    message: str | None = None


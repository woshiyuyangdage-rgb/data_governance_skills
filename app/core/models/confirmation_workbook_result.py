"""Result model for confirmation workbook exports."""

from pydantic import BaseModel


class ConfirmationWorkbookResult(BaseModel):
    """Summary of one exported confirmation workbook."""

    workbook_type: str
    output_path: str
    row_count: int
    status: str
    message: str | None = None


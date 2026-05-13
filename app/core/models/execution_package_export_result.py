"""Result model for execution-ready package exports."""

from pydantic import BaseModel


class ExecutionPackageExportResult(BaseModel):
    """Summary of one execution-ready package export operation."""

    export_format: str
    output_path: str
    package_id: str
    rule_count: int
    status: str
    message: str | None = None

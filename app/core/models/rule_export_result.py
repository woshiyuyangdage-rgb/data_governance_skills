"""Result model for confirmed quality rule exports."""

from pydantic import BaseModel


class RuleExportResult(BaseModel):
    """Summary of one rule asset export operation."""

    export_format: str
    output_path: str
    rule_count: int
    status: str
    message: str | None = None

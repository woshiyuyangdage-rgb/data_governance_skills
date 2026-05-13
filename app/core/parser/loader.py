"""Unified file loader for metadata ingestion."""

from pathlib import Path

from app.core.models.table_meta import TableMeta
from app.core.parser.csv_parser import parse_csv
from app.core.parser.excel_parser import parse_excel
from app.core.parser.parser_exceptions import ParserError, UnsupportedFileFormatError


def load_metadata_file(file_path: str) -> list[TableMeta]:
    """Load metadata rows from a supported local file."""
    path = Path(file_path)
    if not path.exists():
        raise ParserError(f"Input file does not exist: {file_path}")

    extension = path.suffix.lower()
    if extension == ".csv":
        return parse_csv(str(path))
    if extension in {".xlsx", ".xls"}:
        return parse_excel(str(path))

    raise UnsupportedFileFormatError(
        f"Unsupported file format '{extension or '<none>'}'. Supported formats: .csv, .xlsx, .xls."
    )


def load_metadata_with_intake_adapter(
    file_path: str,
    profile_name: str | None = None,
    sheet_name: str | None = None,
) -> list[TableMeta]:
    """Load metadata through intake normalization, then fall back to the standard parser."""
    if profile_name:
        from app.core.intake.intake_adapter_service import IntakeAdapterService

        tables, _match_result, normalization = IntakeAdapterService().load_tables(
            file_path,
            profile_name=profile_name,
            sheet_name=sheet_name,
        )
        if normalization.status != "success":
            raise ParserError(normalization.message or "Intake normalization failed.")
        return tables

    try:
        from app.core.intake.intake_adapter_service import IntakeAdapterService

        tables, _match_result, normalization = IntakeAdapterService().load_tables(
            file_path,
            profile_name=None,
            sheet_name=sheet_name,
        )
        if normalization.status == "success":
            return tables
    except Exception:
        pass

    return load_metadata_file(file_path)

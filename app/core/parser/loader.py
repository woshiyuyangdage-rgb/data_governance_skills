"""Unified file loader for metadata ingestion."""

from functools import lru_cache
from pathlib import Path

from app.core.models.table_meta import TableMeta
from app.core.parser.csv_parser import parse_csv
from app.core.parser.excel_parser import parse_excel
from app.core.parser.parser_exceptions import ParserError, UnsupportedFileFormatError
from app.core.utils.file_utils import LocalPathAccessError, resolve_allowed_local_path


def _file_signature(path: Path) -> str:
    """Build a stable cache token for one local file."""
    try:
        stat = path.stat()
    except FileNotFoundError:
        return str(path)
    return f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"


@lru_cache(maxsize=32)
def _load_metadata_file_cached(file_path: str, file_signature: str) -> tuple[TableMeta, ...]:
    """Load metadata rows from a supported local file with signature-based caching."""
    path = Path(file_path)
    if not path.exists():
        raise ParserError(f"Input file does not exist: {file_path}")

    extension = path.suffix.lower()
    if extension == ".csv":
        return tuple(parse_csv(str(path)))
    if extension in {".xlsx", ".xls"}:
        return tuple(parse_excel(str(path)))

    raise UnsupportedFileFormatError(
        f"Unsupported file format '{extension or '<none>'}'. Supported formats: .csv, .xlsx, .xls."
    )


def load_metadata_file(file_path: str) -> list[TableMeta]:
    """Load metadata rows from a supported local file."""
    try:
        path = resolve_allowed_local_path(file_path, path_label="file_path")
    except LocalPathAccessError as exc:
        raise ParserError(str(exc)) from exc
    return list(_load_metadata_file_cached(str(path), _file_signature(path)))


def load_metadata_with_intake_adapter(
    file_path: str,
    profile_name: str | None = None,
    sheet_name: str | None = None,
) -> list[TableMeta]:
    """Load metadata through intake normalization, then fall back to the standard parser."""
    try:
        resolved_file_path = str(
            resolve_allowed_local_path(file_path, path_label="file_path")
        )
    except LocalPathAccessError as exc:
        raise ParserError(str(exc)) from exc

    if profile_name:
        from app.core.intake.intake_adapter_service import IntakeAdapterService

        tables, _match_result, normalization = IntakeAdapterService().load_tables(
            resolved_file_path,
            profile_name=profile_name,
            sheet_name=sheet_name,
        )
        if normalization.status != "success":
            raise ParserError(normalization.message or "Intake normalization failed.")
        return tables

    try:
        from app.core.intake.intake_adapter_service import IntakeAdapterService

        tables, _match_result, normalization = IntakeAdapterService().load_tables(
            resolved_file_path,
            profile_name=None,
            sheet_name=sheet_name,
        )
        if normalization.status == "success":
            return tables
    except Exception:
        pass

    return load_metadata_file(resolved_file_path)

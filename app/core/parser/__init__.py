"""Parser interfaces for metadata ingestion."""

from app.core.parser.csv_parser import parse_csv
from app.core.parser.excel_parser import parse_excel
from app.core.parser.loader import load_metadata_file
from app.core.parser.parser_exceptions import (
    EmptyInputFileError,
    MissingRequiredColumnsError,
    ParserError,
    UnsupportedFileFormatError,
)

__all__ = [
    "parse_csv",
    "parse_excel",
    "load_metadata_file",
    "ParserError",
    "MissingRequiredColumnsError",
    "EmptyInputFileError",
    "UnsupportedFileFormatError",
]

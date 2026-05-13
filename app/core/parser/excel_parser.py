"""Excel parser for metadata ingestion."""

import pandas as pd

from app.core.models.table_meta import TableMeta
from app.core.parser._shared import dataframe_to_tables
from app.core.parser.parser_exceptions import EmptyInputFileError, ParserError


def parse_excel(file_path: str) -> list[TableMeta]:
    """Read an Excel metadata file and convert rows into table objects."""
    try:
        dataframe = pd.read_excel(file_path)
    except ValueError as exc:
        raise EmptyInputFileError("The Excel file does not contain readable rows.") from exc
    except Exception as exc:
        raise ParserError(f"Failed to read Excel file '{file_path}': {exc}") from exc

    return dataframe_to_tables(dataframe)

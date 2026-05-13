"""CSV parser for metadata ingestion."""

import pandas as pd

from app.core.models.table_meta import TableMeta
from app.core.parser._shared import dataframe_to_tables
from app.core.parser.parser_exceptions import EmptyInputFileError, ParserError


def parse_csv(file_path: str) -> list[TableMeta]:
    """Read a CSV metadata file and convert rows into table objects."""
    try:
        dataframe = pd.read_csv(file_path)
    except pd.errors.EmptyDataError as exc:
        raise EmptyInputFileError("The CSV file is empty.") from exc
    except Exception as exc:
        raise ParserError(f"Failed to read CSV file '{file_path}': {exc}") from exc

    return dataframe_to_tables(dataframe)

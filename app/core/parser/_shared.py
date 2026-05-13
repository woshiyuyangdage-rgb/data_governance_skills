"""Shared helpers for CSV and Excel metadata parsing."""

from collections import OrderedDict

import pandas as pd

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta
from app.core.parser.parser_exceptions import (
    EmptyInputFileError,
    MissingRequiredColumnsError,
    ParserError,
)

STANDARD_COLUMNS = [
    "table_name",
    "table_name_cn",
    "table_description",
    "schema_name",
    "system_name",
    "field_name",
    "field_name_cn",
    "field_description",
    "data_type",
    "nullable",
]
REQUIRED_TABLE_COLUMNS = {"table_name"}
FIELD_LEVEL_COLUMNS = {"field_name", "field_name_cn", "field_description", "data_type", "nullable"}
TRUE_VALUES = {"true", "yes", "1", "y", "是", "可空", "真"}
FALSE_VALUES = {"false", "no", "0", "n", "否", "非空", "不可空", "假"}


def clean_text(value: object) -> str | None:
    """Trim whitespace and normalize blanks to None."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def normalize_nullable(value: object) -> bool | None:
    """Map common nullable tokens to boolean values."""
    normalized = clean_text(value)
    if normalized is None:
        return None

    lowered = normalized.lower()
    if lowered in TRUE_VALUES:
        return True
    if lowered in FALSE_VALUES:
        return False
    return None


def _first_non_null(current: str | None, candidate: str | None) -> str | None:
    if current is not None:
        return current
    return candidate


def prepare_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate shape and normalize raw dataframe columns."""
    normalized_columns = [clean_text(column) or "" for column in dataframe.columns]
    dataframe = dataframe.copy()
    dataframe.columns = normalized_columns

    if not normalized_columns:
        raise EmptyInputFileError("The input file does not contain any columns.")

    missing_table_columns = sorted(REQUIRED_TABLE_COLUMNS - set(normalized_columns))
    if missing_table_columns:
        raise MissingRequiredColumnsError(missing_table_columns, normalized_columns)

    if "field_name" not in normalized_columns:
        present_field_columns = FIELD_LEVEL_COLUMNS.intersection(normalized_columns)
        if present_field_columns:
            raise MissingRequiredColumnsError(["field_name"], normalized_columns)

    dataframe = dataframe.dropna(how="all")
    if dataframe.empty:
        raise EmptyInputFileError("The input file does not contain any data rows.")

    for column in STANDARD_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None

    return dataframe[STANDARD_COLUMNS]


def dataframe_to_tables(dataframe: pd.DataFrame) -> list[TableMeta]:
    """Convert normalized metadata rows into table objects."""
    dataframe = prepare_dataframe(dataframe)
    tables: OrderedDict[str, dict[str, object]] = OrderedDict()

    for row_index, row in enumerate(dataframe.to_dict(orient="records"), start=2):
        table_name = clean_text(row.get("table_name"))
        if table_name is None:
            raise ParserError(
                f"Row {row_index} is missing a required table_name value."
            )

        table_bucket = tables.setdefault(
            table_name,
            {
                "table_name": table_name,
                "table_name_cn": None,
                "table_description": None,
                "schema_name": None,
                "system_name": None,
                "fields": [],
            },
        )

        table_bucket["table_name_cn"] = _first_non_null(
            table_bucket["table_name_cn"],
            clean_text(row.get("table_name_cn")),
        )
        table_bucket["table_description"] = _first_non_null(
            table_bucket["table_description"],
            clean_text(row.get("table_description")),
        )
        table_bucket["schema_name"] = _first_non_null(
            table_bucket["schema_name"],
            clean_text(row.get("schema_name")),
        )
        table_bucket["system_name"] = _first_non_null(
            table_bucket["system_name"],
            clean_text(row.get("system_name")),
        )

        field_name = clean_text(row.get("field_name"))
        if field_name is None:
            continue

        table_bucket["fields"].append(
            FieldMeta(
                field_name=field_name,
                field_name_cn=clean_text(row.get("field_name_cn")),
                field_description=clean_text(row.get("field_description")),
                data_type=clean_text(row.get("data_type")),
                nullable=normalize_nullable(row.get("nullable")),
            )
        )

    return [TableMeta(**table_data) for table_data in tables.values()]


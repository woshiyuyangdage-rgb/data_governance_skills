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
    "business_domain",
    "owner_role",
    "lifecycle_status",
    "data_layer",
    "catalog_path",
    "upstream_systems",
    "downstream_applications",
    "frequent_query_sql",
    "usage_scenarios",
    "standard_code",
    "standard_name",
    "sensitivity_label",
    "primary_key_fields",
    "foreign_key_fields",
    "field_name",
    "field_name_cn",
    "field_description",
    "data_type",
    "data_length",
    "sample_values",
    "nullable",
    "field_standard_code",
    "field_standard_name",
    "field_business_domain",
    "field_owner_role",
    "field_lifecycle_status",
    "field_catalog_path",
    "is_primary_key",
    "is_foreign_key",
    "is_sensitive",
]
REQUIRED_TABLE_COLUMNS = {"table_name"}
FIELD_LEVEL_COLUMNS = {
    "field_name",
    "field_name_cn",
    "field_description",
    "data_type",
    "data_length",
    "sample_values",
    "nullable",
}
TRUE_VALUES = {"true", "yes", "1", "y", "是", "可空", "真"}
FALSE_VALUES = {"false", "no", "0", "n", "否", "非空", "不可空", "假"}
LIST_DELIMITER = ";"


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


def normalize_list_text(value: object) -> list[str]:
    """Split a loose text cell into a list of trimmed values."""
    normalized = clean_text(value)
    if normalized is None:
        return []
    for delimiter in [",", "|", "\n"]:
        normalized = normalized.replace(delimiter, LIST_DELIMITER)
    return [item.strip() for item in normalized.split(LIST_DELIMITER) if item.strip()]


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
                "business_domain": None,
                "owner_role": None,
                "lifecycle_status": None,
                "data_layer": None,
                "catalog_path": None,
                "upstream_systems": [],
                "downstream_applications": [],
                "frequent_query_sql": None,
                "usage_scenarios": None,
                "standard_code": None,
                "standard_name": None,
                "sensitivity_label": None,
                "primary_key_fields": [],
                "foreign_key_fields": [],
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
        table_bucket["business_domain"] = _first_non_null(
            table_bucket["business_domain"],
            clean_text(row.get("business_domain")),
        )
        table_bucket["owner_role"] = _first_non_null(
            table_bucket["owner_role"],
            clean_text(row.get("owner_role")),
        )
        table_bucket["lifecycle_status"] = _first_non_null(
            table_bucket["lifecycle_status"],
            clean_text(row.get("lifecycle_status")),
        )
        table_bucket["data_layer"] = _first_non_null(
            table_bucket["data_layer"],
            clean_text(row.get("data_layer")),
        )
        table_bucket["catalog_path"] = _first_non_null(
            table_bucket["catalog_path"],
            clean_text(row.get("catalog_path")),
        )
        if not table_bucket["upstream_systems"]:
            table_bucket["upstream_systems"] = normalize_list_text(
                row.get("upstream_systems")
            )
        if not table_bucket["downstream_applications"]:
            table_bucket["downstream_applications"] = normalize_list_text(
                row.get("downstream_applications")
            )
        table_bucket["frequent_query_sql"] = _first_non_null(
            table_bucket["frequent_query_sql"],
            clean_text(row.get("frequent_query_sql")),
        )
        table_bucket["usage_scenarios"] = _first_non_null(
            table_bucket["usage_scenarios"],
            clean_text(row.get("usage_scenarios")),
        )
        table_bucket["standard_code"] = _first_non_null(
            table_bucket["standard_code"],
            clean_text(row.get("standard_code")),
        )
        table_bucket["standard_name"] = _first_non_null(
            table_bucket["standard_name"],
            clean_text(row.get("standard_name")),
        )
        table_bucket["sensitivity_label"] = _first_non_null(
            table_bucket["sensitivity_label"],
            clean_text(row.get("sensitivity_label")),
        )
        if not table_bucket["primary_key_fields"]:
            table_bucket["primary_key_fields"] = normalize_list_text(
                row.get("primary_key_fields")
            )
        if not table_bucket["foreign_key_fields"]:
            table_bucket["foreign_key_fields"] = normalize_list_text(
                row.get("foreign_key_fields")
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
                data_length=clean_text(row.get("data_length")),
                sample_values=clean_text(row.get("sample_values")),
                nullable=normalize_nullable(row.get("nullable")),
                standard_code=clean_text(row.get("field_standard_code"))
                or clean_text(row.get("standard_code")),
                standard_name=clean_text(row.get("field_standard_name"))
                or clean_text(row.get("standard_name")),
                business_domain=clean_text(row.get("field_business_domain"))
                or clean_text(row.get("business_domain")),
                owner_role=clean_text(row.get("field_owner_role"))
                or clean_text(row.get("owner_role")),
                is_primary_key=normalize_nullable(row.get("is_primary_key")),
                is_foreign_key=normalize_nullable(row.get("is_foreign_key")),
                is_sensitive=normalize_nullable(row.get("is_sensitive")),
                lifecycle_status=clean_text(row.get("field_lifecycle_status"))
                or clean_text(row.get("lifecycle_status")),
                catalog_path=clean_text(row.get("field_catalog_path"))
                or clean_text(row.get("catalog_path")),
            )
        )

    return [TableMeta(**table_data) for table_data in tables.values()]

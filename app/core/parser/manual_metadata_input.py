"""Manual metadata input helpers.

These helpers turn small hand-entered metadata payloads into the same row-based
shape used by CSV and Excel ingestion, so downstream workflows stay unchanged.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from uuid import uuid4

import pandas as pd

from app.core.models.table_meta import TableMeta
from app.core.parser._shared import STANDARD_COLUMNS, clean_text, dataframe_to_tables
from app.core.parser.parser_exceptions import EmptyInputFileError, ParserError
from app.core.utils.file_utils import ensure_directory, sanitize_filename

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MANUAL_METADATA_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "manual_metadata"
MANUAL_METADATA_COLUMNS = [
    "table_name",
    "table_name_cn",
    "table_description",
    "schema_name",
    "system_name",
    "business_domain",
    "owner_role",
    "lifecycle_status",
    "data_layer",
    "field_name",
    "field_name_cn",
    "field_description",
    "data_type",
    "data_length",
    "sample_values",
    "nullable",
    "field_standard_code",
    "field_standard_name",
    "is_primary_key",
    "is_foreign_key",
    "is_sensitive",
]
TABLE_LEVEL_COLUMNS = [
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
]


def _is_blank_row(row: Mapping[str, object]) -> bool:
    return all(clean_text(value) is None for value in row.values())


def normalize_manual_metadata_records(
    records: Iterable[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Normalize manual metadata rows into the standard parser column shape.

    Blank rows are ignored. Table-level values are carried forward, allowing a
    small manual grid where users type a table once and then add several fields.
    """
    normalized_records: list[dict[str, object]] = []
    last_table_values: dict[str, object] = {}

    for row_number, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise ParserError(f"Manual metadata row {row_number} must be a mapping.")

        row = {column: record.get(column) for column in STANDARD_COLUMNS}
        if _is_blank_row(row):
            continue

        if clean_text(row.get("table_name")) is None and last_table_values:
            for column in TABLE_LEVEL_COLUMNS:
                if clean_text(row.get(column)) is None and column in last_table_values:
                    row[column] = last_table_values[column]

        table_name = clean_text(row.get("table_name"))
        if table_name is None:
            raise ParserError(
                f"Manual metadata row {row_number} is missing a table_name value."
            )

        for column in TABLE_LEVEL_COLUMNS:
            value = row.get(column)
            if clean_text(value) is not None:
                last_table_values[column] = value

        normalized_records.append(row)

    if not normalized_records:
        raise EmptyInputFileError("Manual metadata input does not contain any rows.")

    return normalized_records


def manual_metadata_records_to_dataframe(
    records: Iterable[Mapping[str, object]],
) -> pd.DataFrame:
    """Return normalized manual rows as a stable dataframe."""
    return pd.DataFrame(
        normalize_manual_metadata_records(records),
        columns=STANDARD_COLUMNS,
    )


def manual_metadata_records_to_tables(
    records: Iterable[Mapping[str, object]],
) -> list[TableMeta]:
    """Convert hand-entered metadata rows into table metadata objects."""
    return dataframe_to_tables(manual_metadata_records_to_dataframe(records))


def save_manual_metadata_records(
    records: Iterable[Mapping[str, object]],
    output_dir: str | Path | None = None,
    *,
    base_filename: str | None = None,
) -> str:
    """Persist manual metadata rows as a local CSV file and return its path."""
    dataframe = manual_metadata_records_to_dataframe(records)
    target_dir = Path(output_dir or MANUAL_METADATA_OUTPUT_DIR)
    ensure_directory(target_dir)

    base_name = sanitize_filename(base_filename or "manual_metadata")
    destination = target_dir / f"{Path(base_name).stem}_{uuid4().hex[:8]}.csv"
    dataframe.to_csv(destination, index=False, encoding="utf-8")
    return str(destination)

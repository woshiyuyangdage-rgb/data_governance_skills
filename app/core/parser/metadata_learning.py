"""Local learning memory for metadata completion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.models.table_meta import TableMeta
from app.core.normalize import expand_tokens, normalize_tokens, split_tokens
from app.core.parser.loader import load_metadata_file
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEARNED_METADATA_DIR = PROJECT_ROOT / "app" / "data" / "learned_metadata"
FIELD_MEMORY_PATH = LEARNED_METADATA_DIR / "field_completion_memory.csv"
TABLE_MEMORY_PATH = LEARNED_METADATA_DIR / "table_completion_memory.csv"

FIELD_MEMORY_COLUMNS = [
    "field_key",
    "field_name",
    "field_name_cn",
    "field_description",
    "table_name",
    "table_name_cn",
    "business_domain",
    "source",
]
TABLE_MEMORY_COLUMNS = [
    "table_key",
    "table_name",
    "table_name_cn",
    "table_description",
    "business_domain",
    "source",
]


@dataclass(frozen=True)
class MetadataLearningSummary:
    """Summary of learned metadata memory updates."""

    field_memory_count: int = 0
    table_memory_count: int = 0
    output_dir: str = str(LEARNED_METADATA_DIR)


def metadata_name_key(value: str | None) -> str:
    """Return a normalized key for matching learned metadata names."""
    tokens = normalize_tokens(expand_tokens(split_tokens(value)))
    return "_".join(tokens)


def _empty_dataframe(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _read_memory(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return _empty_dataframe(columns)
    dataframe = pd.read_csv(path)
    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = None
    return dataframe[columns]


def load_field_completion_memory() -> pd.DataFrame:
    """Load learned field-level completion memory."""
    return _read_memory(FIELD_MEMORY_PATH, FIELD_MEMORY_COLUMNS)


def load_table_completion_memory() -> pd.DataFrame:
    """Load learned table-level completion memory."""
    return _read_memory(TABLE_MEMORY_PATH, TABLE_MEMORY_COLUMNS)


def _deduplicate_memory(dataframe: pd.DataFrame, key_column: str) -> pd.DataFrame:
    dataframe = dataframe.copy()
    dataframe = dataframe.dropna(how="all")
    if dataframe.empty:
        return dataframe
    return dataframe.drop_duplicates(subset=[key_column], keep="last")


def extract_learning_memory_from_tables(
    tables: list[TableMeta],
    *,
    source: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract reusable table/field completion memory from high-quality metadata."""
    table_rows: list[dict[str, object]] = []
    field_rows: list[dict[str, object]] = []

    for table in tables:
        table_key = metadata_name_key(table.table_name)
        if table_key and (table.table_name_cn or table.table_description):
            table_rows.append(
                {
                    "table_key": table_key,
                    "table_name": table.table_name,
                    "table_name_cn": table.table_name_cn,
                    "table_description": table.table_description,
                    "business_domain": table.business_domain,
                    "source": source,
                }
            )
        for field_meta in table.fields:
            field_key = metadata_name_key(field_meta.field_name)
            if not field_key:
                continue
            if not (field_meta.field_name_cn or field_meta.field_description):
                continue
            field_rows.append(
                {
                    "field_key": field_key,
                    "field_name": field_meta.field_name,
                    "field_name_cn": field_meta.field_name_cn,
                    "field_description": field_meta.field_description,
                    "table_name": table.table_name,
                    "table_name_cn": table.table_name_cn,
                    "business_domain": field_meta.business_domain
                    or table.business_domain,
                    "source": source,
                }
            )

    return (
        pd.DataFrame(field_rows, columns=FIELD_MEMORY_COLUMNS),
        pd.DataFrame(table_rows, columns=TABLE_MEMORY_COLUMNS),
    )


def learn_metadata_memory_from_tables(
    tables: list[TableMeta],
    *,
    source: str,
    output_dir: str | Path | None = None,
) -> MetadataLearningSummary:
    """Merge high-quality metadata into the local completion memory."""
    target_dir = Path(output_dir or LEARNED_METADATA_DIR)
    ensure_directory(target_dir)
    field_path = target_dir / FIELD_MEMORY_PATH.name
    table_path = target_dir / TABLE_MEMORY_PATH.name

    field_rows, table_rows = extract_learning_memory_from_tables(tables, source=source)
    existing_fields = _read_memory(field_path, FIELD_MEMORY_COLUMNS)
    existing_tables = _read_memory(table_path, TABLE_MEMORY_COLUMNS)

    merged_fields = _deduplicate_memory(
        pd.concat([existing_fields, field_rows], ignore_index=True),
        "field_key",
    )
    merged_tables = _deduplicate_memory(
        pd.concat([existing_tables, table_rows], ignore_index=True),
        "table_key",
    )
    merged_fields.to_csv(field_path, index=False, encoding="utf-8")
    merged_tables.to_csv(table_path, index=False, encoding="utf-8")

    return MetadataLearningSummary(
        field_memory_count=len(merged_fields),
        table_memory_count=len(merged_tables),
        output_dir=str(target_dir),
    )


def learn_metadata_memory_from_file(
    file_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> MetadataLearningSummary:
    """Learn completion memory from one high-quality metadata file."""
    return learn_metadata_memory_from_tables(
        load_metadata_file(str(file_path)),
        source=str(file_path),
        output_dir=output_dir,
    )


def learn_metadata_memory_from_dataframe(
    dataframe: pd.DataFrame,
    *,
    source: str,
    output_dir: str | Path | None = None,
) -> MetadataLearningSummary:
    """Learn completion memory from a reviewed standard-shape metadata dataframe."""
    from app.core.parser._shared import dataframe_to_tables

    return learn_metadata_memory_from_tables(
        dataframe_to_tables(dataframe),
        source=source,
        output_dir=output_dir,
    )

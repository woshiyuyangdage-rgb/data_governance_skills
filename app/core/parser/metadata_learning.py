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


@dataclass(frozen=True)
class MetadataCompletionMemoryHealth:
    """Health summary for learned metadata completion memory."""

    field_memory_count: int = 0
    table_memory_count: int = 0
    field_key_count: int = 0
    table_key_count: int = 0
    conflict_field_key_count: int = 0
    conflict_table_key_count: int = 0
    invalid_field_record_count: int = 0
    invalid_table_record_count: int = 0
    conflict_field_keys: tuple[str, ...] = ()
    conflict_table_keys: tuple[str, ...] = ()
    invalid_field_record_keys: tuple[str, ...] = ()
    invalid_table_record_keys: tuple[str, ...] = ()


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


def _prepare_memory(
    dataframe: pd.DataFrame | None,
    columns: list[str],
) -> pd.DataFrame:
    if dataframe is None or dataframe.empty:
        return _empty_dataframe(columns)
    prepared = dataframe.copy()
    for column in columns:
        if column not in prepared.columns:
            prepared[column] = None
    prepared = prepared[columns].astype(object)
    return prepared.where(pd.notna(prepared), None)


def _has_text(value: object) -> bool:
    return bool(str(value or "").strip())


def _distinct_text_values(rows: pd.DataFrame, column: str) -> set[str]:
    if column not in rows.columns:
        return set()
    return {
        str(value).strip()
        for value in rows[column].tolist()
        if _has_text(value)
    }


def _conflict_keys(
    dataframe: pd.DataFrame,
    *,
    key_column: str,
    target_columns: tuple[str, ...],
) -> tuple[str, ...]:
    if dataframe.empty:
        return ()
    valid_rows = dataframe[dataframe[key_column].map(_has_text)]
    conflict_keys: list[str] = []
    for key, group in valid_rows.groupby(key_column):
        if any(len(_distinct_text_values(group, column)) > 1 for column in target_columns):
            conflict_keys.append(str(key))
    return tuple(sorted(set(conflict_keys)))


def _field_invalid_mask(dataframe: pd.DataFrame) -> pd.Series:
    missing_key = ~dataframe["field_key"].map(_has_text)
    missing_content = (
        ~dataframe["field_name_cn"].map(_has_text)
        & ~dataframe["field_description"].map(_has_text)
    )
    return missing_key | missing_content


def _table_invalid_mask(dataframe: pd.DataFrame) -> pd.Series:
    missing_key = ~dataframe["table_key"].map(_has_text)
    missing_content = (
        ~dataframe["table_name_cn"].map(_has_text)
        & ~dataframe["table_description"].map(_has_text)
    )
    return missing_key | missing_content


def summarize_metadata_completion_memory(
    field_memory: pd.DataFrame | None = None,
    table_memory: pd.DataFrame | None = None,
) -> MetadataCompletionMemoryHealth:
    """Return a maintenance-friendly summary for metadata completion memory."""
    fields = _prepare_memory(
        field_memory if field_memory is not None else load_field_completion_memory(),
        FIELD_MEMORY_COLUMNS,
    )
    tables = _prepare_memory(
        table_memory if table_memory is not None else load_table_completion_memory(),
        TABLE_MEMORY_COLUMNS,
    )

    field_invalid_rows = fields[_field_invalid_mask(fields)] if not fields.empty else fields
    table_invalid_rows = tables[_table_invalid_mask(tables)] if not tables.empty else tables
    conflict_field_keys = _conflict_keys(
        fields,
        key_column="field_key",
        target_columns=("field_name_cn", "field_description"),
    )
    conflict_table_keys = _conflict_keys(
        tables,
        key_column="table_key",
        target_columns=("table_name_cn", "table_description"),
    )

    field_keys = {
        str(value).strip()
        for value in fields["field_key"].tolist()
        if _has_text(value)
    }
    table_keys = {
        str(value).strip()
        for value in tables["table_key"].tolist()
        if _has_text(value)
    }
    invalid_field_record_keys = sorted(
        {
            f"{row.get('table_name') or 'missing_table'}:{row.get('field_key') or 'missing_field'}"
            for _, row in field_invalid_rows.iterrows()
        }
    )
    invalid_table_record_keys = sorted(
        {
            str(row.get("table_key") or row.get("table_name") or "missing_table")
            for _, row in table_invalid_rows.iterrows()
        }
    )

    return MetadataCompletionMemoryHealth(
        field_memory_count=len(fields),
        table_memory_count=len(tables),
        field_key_count=len(field_keys),
        table_key_count=len(table_keys),
        conflict_field_key_count=len(conflict_field_keys),
        conflict_table_key_count=len(conflict_table_keys),
        invalid_field_record_count=len(field_invalid_rows),
        invalid_table_record_count=len(table_invalid_rows),
        conflict_field_keys=conflict_field_keys,
        conflict_table_keys=conflict_table_keys,
        invalid_field_record_keys=tuple(invalid_field_record_keys),
        invalid_table_record_keys=tuple(invalid_table_record_keys),
    )


def metadata_completion_memory_details(
    field_memory: pd.DataFrame | None = None,
    table_memory: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Return metadata completion memory records that need review."""
    fields = _prepare_memory(
        field_memory if field_memory is not None else load_field_completion_memory(),
        FIELD_MEMORY_COLUMNS,
    )
    tables = _prepare_memory(
        table_memory if table_memory is not None else load_table_completion_memory(),
        TABLE_MEMORY_COLUMNS,
    )
    if fields.empty and tables.empty:
        return {
            "field_conflict_records": [],
            "table_conflict_records": [],
            "invalid_field_records": [],
            "invalid_table_records": [],
        }

    conflict_field_keys = set(
        _conflict_keys(
            fields,
            key_column="field_key",
            target_columns=("field_name_cn", "field_description"),
        )
    )
    conflict_table_keys = set(
        _conflict_keys(
            tables,
            key_column="table_key",
            target_columns=("table_name_cn", "table_description"),
        )
    )
    field_invalid_rows = fields[_field_invalid_mask(fields)] if not fields.empty else fields
    table_invalid_rows = tables[_table_invalid_mask(tables)] if not tables.empty else tables

    return {
        "field_conflict_records": fields[
            fields["field_key"].astype(str).isin(conflict_field_keys)
        ].to_dict("records"),
        "table_conflict_records": tables[
            tables["table_key"].astype(str).isin(conflict_table_keys)
        ].to_dict("records"),
        "invalid_field_records": field_invalid_rows.to_dict("records"),
        "invalid_table_records": table_invalid_rows.to_dict("records"),
    }


def _metadata_memory_paths(
    output_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    if output_dir is None:
        return FIELD_MEMORY_PATH, TABLE_MEMORY_PATH
    target_dir = Path(output_dir)
    return target_dir / FIELD_MEMORY_PATH.name, target_dir / TABLE_MEMORY_PATH.name


def _prune_memory_file(
    path: Path,
    columns: list[str],
    invalid_mask_builder,
) -> dict[str, object]:
    if not path.exists():
        return {
            "path": str(path),
            "before_count": 0,
            "removed_count": 0,
            "after_count": 0,
        }

    dataframe = _prepare_memory(_read_memory(path, columns), columns)
    invalid_mask = invalid_mask_builder(dataframe)
    cleaned = dataframe[~invalid_mask]
    cleaned.to_csv(path, index=False, encoding="utf-8")
    return {
        "path": str(path),
        "before_count": len(dataframe),
        "removed_count": int(invalid_mask.sum()),
        "after_count": len(cleaned),
    }


def prune_invalid_metadata_completion_memory(
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Remove invalid learned metadata completion records from local memory."""
    field_path, table_path = _metadata_memory_paths(output_dir)
    field_result = _prune_memory_file(
        field_path,
        FIELD_MEMORY_COLUMNS,
        _field_invalid_mask,
    )
    table_result = _prune_memory_file(
        table_path,
        TABLE_MEMORY_COLUMNS,
        _table_invalid_mask,
    )
    removed_count = int(field_result["removed_count"]) + int(
        table_result["removed_count"]
    )
    return {
        "field_memory": field_result,
        "table_memory": table_result,
        "removed_count": removed_count,
        "summary": f"Removed {removed_count} invalid metadata completion records.",
    }


def clear_metadata_completion_memory_by_field_key(
    field_key: str,
    path: str | Path | None = None,
) -> dict[str, object]:
    """Remove learned metadata completion records for one normalized field key."""
    raw_key = str(field_key or "").strip()
    normalized_key = metadata_name_key(field_key) or raw_key
    match_keys = {key for key in (normalized_key, raw_key) if key}
    memory_path = Path(path or FIELD_MEMORY_PATH)
    if not normalized_key:
        return {
            "path": str(memory_path),
            "field_key": normalized_key,
            "before_count": 0,
            "removed_count": 0,
            "after_count": 0,
            "status": "missing_field_key",
        }
    if not memory_path.exists():
        return {
            "path": str(memory_path),
            "field_key": normalized_key,
            "before_count": 0,
            "removed_count": 0,
            "after_count": 0,
            "status": "not_found",
        }

    dataframe = _prepare_memory(
        _read_memory(memory_path, FIELD_MEMORY_COLUMNS),
        FIELD_MEMORY_COLUMNS,
    )
    remove_mask = dataframe["field_key"].astype(str).isin(match_keys)
    cleaned = dataframe[~remove_mask]
    cleaned.to_csv(memory_path, index=False, encoding="utf-8")
    removed_count = int(remove_mask.sum())
    return {
        "path": str(memory_path),
        "field_key": normalized_key,
        "before_count": len(dataframe),
        "removed_count": removed_count,
        "after_count": len(cleaned),
        "status": "cleared" if removed_count else "not_found",
    }


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

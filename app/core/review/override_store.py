"""Local CSV-backed storage for human review overrides."""

from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.stg_review_record import StgReviewRecord
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OVERRIDES_DIR = PROJECT_ROOT / "app" / "data" / "overrides"
REVIEW_HISTORY_DIR = PROJECT_ROOT / "app" / "data" / "review_history"
REVIEW_SESSIONS_DIR = REVIEW_HISTORY_DIR / "review_sessions"
MAPPING_OVERRIDES_PATH = OVERRIDES_DIR / "mapping_overrides.csv"
STG_OVERRIDES_PATH = OVERRIDES_DIR / "stg_overrides.csv"

MAPPING_OVERRIDE_COLUMNS = [
    "table_name",
    "field_name",
    "original_recommended_standard_code",
    "final_standard_code",
    "review_action",
    "reviewer_note",
    "reviewed_at",
    "source",
]
STG_OVERRIDE_COLUMNS = [
    "source_table_name",
    "source_field_name",
    "original_recommended_stg_field_name",
    "final_stg_field_name",
    "original_recommended_data_type",
    "final_data_type",
    "review_action",
    "reviewer_note",
    "reviewed_at",
    "source",
]


def _read_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)

    dataframe = pd.read_csv(path)
    for column in columns:
        if column not in dataframe.columns:
            dataframe[column] = None
    selected = dataframe[columns].astype(object)
    return selected.where(pd.notna(selected), None)


def _write_csv(path: Path, records: list[dict[str, object]], columns: list[str]) -> str:
    ensure_directory(path.parent)
    dataframe = pd.DataFrame(records, columns=columns)
    dataframe.to_csv(path, index=False, encoding="utf-8")
    return str(path)


def _merge_by_key(
    existing_records: list[dict[str, object]],
    new_records: list[dict[str, object]],
    key_fields: list[str],
) -> list[dict[str, object]]:
    merged: dict[tuple[str, ...], dict[str, object]] = {}
    for record in existing_records + new_records:
        key = tuple(str(record.get(field, "") or "") for field in key_fields)
        merged[key] = record
    return list(merged.values())


def _save_review_session_snapshot(session_type: str, records: list[dict[str, object]]) -> str:
    ensure_directory(REVIEW_SESSIONS_DIR)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    session_path = REVIEW_SESSIONS_DIR / f"{session_type}_{timestamp}.json"
    session_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(session_path)


def load_mapping_overrides() -> list[MappingReviewRecord]:
    """Load locally persisted mapping overrides."""
    dataframe = _read_csv(MAPPING_OVERRIDES_PATH, MAPPING_OVERRIDE_COLUMNS)
    return [MappingReviewRecord(**row) for row in dataframe.to_dict("records")]


def save_mapping_review_records(records: list[MappingReviewRecord]) -> dict[str, str | int]:
    """Persist mapping review records and write a review history snapshot."""
    new_records = [record.model_dump() for record in records]
    existing_records = [record.model_dump() for record in load_mapping_overrides()]
    merged = _merge_by_key(existing_records, new_records, ["table_name", "field_name"])
    csv_path = _write_csv(MAPPING_OVERRIDES_PATH, merged, MAPPING_OVERRIDE_COLUMNS)
    history_path = _save_review_session_snapshot("mapping_review", new_records)
    return {"path": csv_path, "history_path": history_path, "saved_count": len(records)}


def build_mapping_override_lookup(
    records: list[MappingReviewRecord] | None = None,
) -> dict[str, MappingReviewRecord]:
    """Build a lookup for mapping overrides by table and field key."""
    records = records if records is not None else load_mapping_overrides()
    return {f"{record.table_name}.{record.field_name}": record for record in records}


def load_stg_overrides() -> list[StgReviewRecord]:
    """Load locally persisted STG overrides."""
    dataframe = _read_csv(STG_OVERRIDES_PATH, STG_OVERRIDE_COLUMNS)
    return [StgReviewRecord(**row) for row in dataframe.to_dict("records")]


def save_stg_review_records(records: list[StgReviewRecord]) -> dict[str, str | int]:
    """Persist STG review records and write a review history snapshot."""
    new_records = [record.model_dump() for record in records]
    existing_records = [record.model_dump() for record in load_stg_overrides()]
    merged = _merge_by_key(
        existing_records,
        new_records,
        ["source_table_name", "source_field_name"],
    )
    csv_path = _write_csv(STG_OVERRIDES_PATH, merged, STG_OVERRIDE_COLUMNS)
    history_path = _save_review_session_snapshot("stg_review", new_records)
    return {"path": csv_path, "history_path": history_path, "saved_count": len(records)}


def build_stg_override_lookup(
    records: list[StgReviewRecord] | None = None,
) -> dict[str, StgReviewRecord]:
    """Build a lookup for STG overrides by source table and field key."""
    records = records if records is not None else load_stg_overrides()
    return {
        f"{record.source_table_name}.{record.source_field_name}": record for record in records
    }


# TODO: replace flat-file override storage with database-backed persistence when local single-user mode is no longer enough.

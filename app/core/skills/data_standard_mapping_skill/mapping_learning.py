"""Local learning memory for human-reviewed standard mappings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.normalize import expand_tokens, normalize_tokens, split_tokens
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[4]
LEARNED_MAPPING_DIR = PROJECT_ROOT / "app" / "data" / "learned_mapping"
STANDARD_MAPPING_MEMORY_PATH = LEARNED_MAPPING_DIR / "standard_mapping_memory.csv"

STANDARD_MAPPING_MEMORY_COLUMNS = [
    "field_key",
    "table_name",
    "field_name",
    "standard_code",
    "source",
    "review_action",
    "reviewed_at",
]
LEARNABLE_REVIEW_ACTIONS = {"accept", "edit"}


@dataclass(frozen=True)
class StandardMappingLearningSummary:
    """Summary of learned standard-mapping memory updates."""

    learned_count: int = 0
    memory_count: int = 0
    output_path: str = str(STANDARD_MAPPING_MEMORY_PATH)


@dataclass(frozen=True)
class LearnedStandardMapping:
    """One reusable mapping learned from human review."""

    field_key: str
    standard_code: str
    source: str | None = None
    review_action: str | None = None
    reviewed_at: str | None = None


def standard_mapping_memory_key(value: str | None) -> str:
    """Return a normalized field key for standard-mapping memory lookup."""
    tokens = normalize_tokens(expand_tokens(split_tokens(value)))
    return "_".join(tokens)


def _empty_memory() -> pd.DataFrame:
    return pd.DataFrame(columns=STANDARD_MAPPING_MEMORY_COLUMNS)


def _read_memory(path: Path) -> pd.DataFrame:
    if not path.exists():
        return _empty_memory()
    dataframe = pd.read_csv(path)
    for column in STANDARD_MAPPING_MEMORY_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None
    selected = dataframe[STANDARD_MAPPING_MEMORY_COLUMNS].astype(object)
    return selected.where(pd.notna(selected), None)


def load_standard_mapping_memory(path: str | Path | None = None) -> pd.DataFrame:
    """Load learned standard-mapping memory."""
    return _read_memory(Path(path or STANDARD_MAPPING_MEMORY_PATH))


def _record_to_memory_row(record: MappingReviewRecord) -> dict[str, object] | None:
    if record.review_action not in LEARNABLE_REVIEW_ACTIONS:
        return None
    if not record.final_standard_code:
        return None
    field_key = standard_mapping_memory_key(record.field_name)
    if not field_key:
        return None
    return {
        "field_key": field_key,
        "table_name": record.table_name,
        "field_name": record.field_name,
        "standard_code": record.final_standard_code,
        "source": record.source,
        "review_action": record.review_action,
        "reviewed_at": record.reviewed_at,
    }


def learn_standard_mapping_memory_from_review_records(
    records: list[MappingReviewRecord],
    *,
    output_dir: str | Path | None = None,
) -> StandardMappingLearningSummary:
    """Merge accepted/edited review records into the local mapping memory."""
    target_dir = Path(output_dir or LEARNED_MAPPING_DIR)
    ensure_directory(target_dir)
    memory_path = target_dir / STANDARD_MAPPING_MEMORY_PATH.name
    new_rows = [
        row
        for row in (_record_to_memory_row(record) for record in records)
        if row is not None
    ]

    existing = _read_memory(memory_path)
    merged = pd.concat(
        [existing, pd.DataFrame(new_rows, columns=STANDARD_MAPPING_MEMORY_COLUMNS)],
        ignore_index=True,
    )
    if not merged.empty:
        merged = merged.dropna(how="all")
        merged = merged.drop_duplicates(subset=["field_key"], keep="last")
    merged.to_csv(memory_path, index=False, encoding="utf-8")

    return StandardMappingLearningSummary(
        learned_count=len(new_rows),
        memory_count=len(merged),
        output_path=str(memory_path),
    )


def lookup_learned_standard_mapping(
    field_name: str | None,
    memory: pd.DataFrame | None = None,
) -> LearnedStandardMapping | None:
    """Find a learned standard mapping for a field name."""
    field_key = standard_mapping_memory_key(field_name)
    if not field_key:
        return None
    dataframe = memory if memory is not None else load_standard_mapping_memory()
    if dataframe is None or dataframe.empty or "field_key" not in dataframe.columns:
        return None
    matches = dataframe[dataframe["field_key"].astype(str) == field_key]
    if matches.empty:
        return None
    row = matches.iloc[-1]
    standard_code = str(row.get("standard_code") or "").strip()
    if not standard_code:
        return None
    return LearnedStandardMapping(
        field_key=field_key,
        standard_code=standard_code,
        source=str(row.get("source") or "") or None,
        review_action=str(row.get("review_action") or "") or None,
        reviewed_at=str(row.get("reviewed_at") or "") or None,
    )

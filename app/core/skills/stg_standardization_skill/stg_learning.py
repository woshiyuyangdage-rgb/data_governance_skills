"""Local learning memory for human-reviewed STG field suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.models.stg_review_record import StgReviewRecord
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.normalize import clean_text, split_tokens
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[4]
LEARNED_STG_DIR = PROJECT_ROOT / "app" / "data" / "learned_stg"
STG_FIELD_MEMORY_PATH = LEARNED_STG_DIR / "stg_field_memory.csv"

STG_FIELD_MEMORY_COLUMNS = [
    "field_key",
    "source_table_name",
    "source_field_name",
    "final_stg_field_name",
    "final_data_type",
    "source",
    "review_action",
    "reviewed_at",
]
LEARNABLE_REVIEW_ACTIONS = {"accept", "edit"}


@dataclass(frozen=True)
class StgLearningSummary:
    """Summary of learned STG memory updates."""

    learned_count: int = 0
    memory_count: int = 0
    output_path: str = str(STG_FIELD_MEMORY_PATH)


@dataclass(frozen=True)
class LearnedStgField:
    """One reusable STG field decision learned from human review."""

    field_key: str
    final_stg_field_name: str
    final_data_type: str | None = None
    source: str | None = None
    review_action: str | None = None
    reviewed_at: str | None = None


def stg_field_memory_key(value: str | None) -> str:
    """Return a normalized source-field key for STG memory lookup."""
    tokens = split_tokens(clean_text(value or "", lower=False))
    return "_".join(tokens) or clean_text(value or "").replace(" ", "_")


def _empty_memory() -> pd.DataFrame:
    return pd.DataFrame(columns=STG_FIELD_MEMORY_COLUMNS)


def _read_memory(path: Path) -> pd.DataFrame:
    if not path.exists():
        return _empty_memory()
    dataframe = pd.read_csv(path)
    for column in STG_FIELD_MEMORY_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None
    selected = dataframe[STG_FIELD_MEMORY_COLUMNS].astype(object)
    return selected.where(pd.notna(selected), None)


def load_stg_field_memory(path: str | Path | None = None) -> pd.DataFrame:
    """Load learned STG field memory."""
    return _read_memory(Path(path or STG_FIELD_MEMORY_PATH))


def _record_to_memory_row(record: StgReviewRecord) -> dict[str, object] | None:
    if record.review_action not in LEARNABLE_REVIEW_ACTIONS:
        return None
    final_name = record.final_stg_field_name or record.original_recommended_stg_field_name
    if not final_name:
        return None
    field_key = stg_field_memory_key(record.source_field_name)
    if not field_key:
        return None
    return {
        "field_key": field_key,
        "source_table_name": record.source_table_name,
        "source_field_name": record.source_field_name,
        "final_stg_field_name": final_name,
        "final_data_type": record.final_data_type or record.original_recommended_data_type,
        "source": record.source,
        "review_action": record.review_action,
        "reviewed_at": record.reviewed_at,
    }


def learn_stg_memory_from_review_records(
    records: list[StgReviewRecord],
    *,
    output_dir: str | Path | None = None,
) -> StgLearningSummary:
    """Merge accepted/edited STG review records into local memory."""
    target_dir = Path(output_dir or LEARNED_STG_DIR)
    ensure_directory(target_dir)
    memory_path = target_dir / STG_FIELD_MEMORY_PATH.name
    new_rows = [
        row
        for row in (_record_to_memory_row(record) for record in records)
        if row is not None
    ]

    existing = _read_memory(memory_path)
    merged = pd.concat(
        [existing, pd.DataFrame(new_rows, columns=STG_FIELD_MEMORY_COLUMNS)],
        ignore_index=True,
    )
    if not merged.empty:
        merged = merged.dropna(how="all")
        merged = merged.drop_duplicates(subset=["field_key"], keep="last")
    merged.to_csv(memory_path, index=False, encoding="utf-8")

    return StgLearningSummary(
        learned_count=len(new_rows),
        memory_count=len(merged),
        output_path=str(memory_path),
    )


def lookup_learned_stg_field(
    source_field_name: str | None,
    memory: pd.DataFrame | None = None,
) -> LearnedStgField | None:
    """Find a learned STG field decision for a source field."""
    field_key = stg_field_memory_key(source_field_name)
    if not field_key:
        return None
    dataframe = memory if memory is not None else load_stg_field_memory()
    if dataframe is None or dataframe.empty or "field_key" not in dataframe.columns:
        return None
    matches = dataframe[dataframe["field_key"].astype(str) == field_key]
    if matches.empty:
        return None
    row = matches.iloc[-1]
    final_name = str(row.get("final_stg_field_name") or "").strip()
    if not final_name:
        return None
    final_type = str(row.get("final_data_type") or "").strip() or None
    return LearnedStgField(
        field_key=field_key,
        final_stg_field_name=final_name,
        final_data_type=final_type,
        source=str(row.get("source") or "") or None,
        review_action=str(row.get("review_action") or "") or None,
        reviewed_at=str(row.get("reviewed_at") or "") or None,
    )


def apply_learned_stg_field(
    suggestion: StgFieldSuggestion,
    learned_field: LearnedStgField | None,
) -> StgFieldSuggestion:
    """Apply learned STG naming/type hints to one suggestion."""
    if learned_field is None:
        return suggestion

    payload = suggestion.model_dump()
    payload["recommended_stg_field_name"] = learned_field.final_stg_field_name
    if learned_field.final_data_type:
        payload["recommended_data_type"] = learned_field.final_data_type
    payload["mapping_source"] = "learned_stg_memory"
    payload["action"] = "rename"
    evidence = (
        "learned_from_stg_review_history "
        f"field_key={learned_field.field_key} "
        f"source={learned_field.source or 'review'} "
        f"action={learned_field.review_action or 'unknown'}"
    )
    payload["notes"] = f"{suggestion.notes} {evidence}" if suggestion.notes else evidence
    return StgFieldSuggestion(**payload)

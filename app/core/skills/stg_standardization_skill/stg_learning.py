"""Local learning memory for human-reviewed STG field suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.normalize import clean_text, split_tokens
from app.core.utils.file_utils import ensure_directory

PROJECT_ROOT = Path(__file__).resolve().parents[4]
LEARNED_STG_DIR = PROJECT_ROOT / "app" / "data" / "learned_stg"
STG_FIELD_MEMORY_PATH = LEARNED_STG_DIR / "stg_field_memory.csv"

STG_FIELD_MEMORY_COLUMNS = [
    "table_key",
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
GENERIC_FIELD_TOKENS = {
    "amount",
    "code",
    "date",
    "description",
    "flag",
    "identifier",
    "name",
    "number",
    "status",
    "time",
    "type",
    "value",
}


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
    table_key: str | None = None
    match_scope: str = "field"
    conflict_count: int = 0
    source: str | None = None
    review_action: str | None = None
    reviewed_at: str | None = None


@dataclass(frozen=True)
class StgMemoryLookup:
    """Explainable lookup result for learned STG memory."""

    field_key: str = ""
    table_key: str | None = None
    status: str = "not_found"
    reason: str = ""
    record_count: int = 0
    conflict_count: int = 0
    learned_field: LearnedStgField | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class StgMemoryHealth:
    """Health summary for learned STG memory."""

    memory_count: int = 0
    field_key_count: int = 0
    table_key_count: int = 0
    reusable_field_count: int = 0
    generic_field_count: int = 0
    conflict_field_count: int = 0
    invalid_record_count: int = 0
    conflict_field_keys: tuple[str, ...] = ()
    generic_field_keys: tuple[str, ...] = ()
    invalid_record_keys: tuple[str, ...] = ()


def stg_field_memory_key(value: str | None) -> str:
    """Return a normalized source-field key for STG memory lookup."""
    tokens = split_tokens(clean_text(value or "", lower=False))
    return "_".join(tokens) or clean_text(value or "").replace(" ", "_")


def stg_table_memory_key(value: str | None) -> str:
    """Return a normalized source-table key for scoped STG memory lookup."""
    return stg_field_memory_key(value)


def _allows_cross_table_reuse(field_key: str) -> bool:
    tokens = [token for token in field_key.split("_") if token]
    if len(tokens) < 2:
        return False
    return any(token not in GENERIC_FIELD_TOKENS for token in tokens)


def _row_table_key(row: pd.Series) -> str:
    raw_table_key = str(row.get("table_key") or "").strip()
    if raw_table_key:
        return raw_table_key
    return stg_table_memory_key(str(row.get("source_table_name") or ""))


def _distinct_targets(rows: pd.DataFrame, target_column: str) -> set[str]:
    if target_column not in rows.columns:
        return set()
    return {
        str(value).strip()
        for value in rows[target_column].tolist()
        if str(value or "").strip()
    }


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


def summarize_stg_field_memory(
    memory: pd.DataFrame | None = None,
) -> StgMemoryHealth:
    """Return a maintenance-friendly health summary for STG memory."""
    dataframe = memory if memory is not None else load_stg_field_memory()
    if dataframe is None or dataframe.empty:
        return StgMemoryHealth()

    prepared = dataframe.copy()
    for column in STG_FIELD_MEMORY_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None
    prepared = prepared[STG_FIELD_MEMORY_COLUMNS].astype(object)
    prepared = prepared.where(pd.notna(prepared), None)

    valid_field_rows = prepared[
        prepared["field_key"].map(lambda value: bool(str(value or "").strip()))
    ]
    valid_target_rows = valid_field_rows[
        valid_field_rows["final_stg_field_name"].map(
            lambda value: bool(str(value or "").strip())
        )
    ]
    invalid_rows = prepared[
        ~prepared.index.isin(valid_target_rows.index)
        | ~prepared["table_key"].map(lambda value: bool(str(value or "").strip()))
    ]

    field_keys = sorted(
        {
            str(value).strip()
            for value in valid_field_rows["field_key"].tolist()
            if str(value or "").strip()
        }
    )
    table_keys = sorted(
        {
            str(value).strip()
            for value in valid_field_rows["table_key"].tolist()
            if str(value or "").strip()
        }
    )
    conflict_field_keys: list[str] = []
    generic_field_keys: list[str] = []
    reusable_field_keys: list[str] = []
    for field_key, group in valid_target_rows.groupby("field_key"):
        field_key_text = str(field_key)
        if not _allows_cross_table_reuse(field_key_text):
            generic_field_keys.append(field_key_text)
        else:
            reusable_field_keys.append(field_key_text)
        if len(_distinct_targets(group, "final_stg_field_name")) > 1:
            conflict_field_keys.append(field_key_text)

    invalid_record_keys = sorted(
        {
            f"{row.get('table_key') or 'missing_table'}:{row.get('field_key') or 'missing_field'}"
            for _, row in invalid_rows.iterrows()
        }
    )

    return StgMemoryHealth(
        memory_count=len(prepared),
        field_key_count=len(field_keys),
        table_key_count=len(table_keys),
        reusable_field_count=len(set(reusable_field_keys)),
        generic_field_count=len(set(generic_field_keys)),
        conflict_field_count=len(set(conflict_field_keys)),
        invalid_record_count=len(invalid_rows),
        conflict_field_keys=tuple(sorted(set(conflict_field_keys))),
        generic_field_keys=tuple(sorted(set(generic_field_keys))),
        invalid_record_keys=tuple(invalid_record_keys),
    )


def stg_field_memory_details(
    memory: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Return conflict, generic, and invalid learned STG records."""
    dataframe = memory if memory is not None else load_stg_field_memory()
    if dataframe is None or dataframe.empty:
        return {
            "conflict_records": [],
            "generic_records": [],
            "invalid_records": [],
        }

    prepared = dataframe.copy()
    for column in STG_FIELD_MEMORY_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None
    prepared = prepared[STG_FIELD_MEMORY_COLUMNS].astype(object)
    prepared = prepared.where(pd.notna(prepared), None)

    missing_field = ~prepared["field_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_table = ~prepared["table_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_target = ~prepared["final_stg_field_name"].map(
        lambda value: bool(str(value or "").strip())
    )
    invalid_rows = prepared[missing_field | missing_table | missing_target]
    valid_rows = prepared[~missing_field & ~missing_target]

    conflict_field_keys = {
        str(field_key)
        for field_key, group in valid_rows.groupby("field_key")
        if len(_distinct_targets(group, "final_stg_field_name")) > 1
    }
    generic_field_keys = {
        str(field_key)
        for field_key in valid_rows["field_key"].tolist()
        if str(field_key or "").strip()
        and not _allows_cross_table_reuse(str(field_key))
    }

    return {
        "conflict_records": valid_rows[
            valid_rows["field_key"].astype(str).isin(conflict_field_keys)
        ].to_dict("records"),
        "generic_records": valid_rows[
            valid_rows["field_key"].astype(str).isin(generic_field_keys)
        ].to_dict("records"),
        "invalid_records": invalid_rows.to_dict("records"),
    }


def prune_invalid_stg_field_memory(
    path: str | Path | None = None,
) -> dict[str, object]:
    """Remove invalid learned STG records from local memory."""
    memory_path = Path(path or STG_FIELD_MEMORY_PATH)
    if not memory_path.exists():
        return {
            "path": str(memory_path),
            "before_count": 0,
            "removed_count": 0,
            "after_count": 0,
        }

    dataframe = _read_memory(memory_path)
    missing_field = ~dataframe["field_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_table = ~dataframe["table_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_target = ~dataframe["final_stg_field_name"].map(
        lambda value: bool(str(value or "").strip())
    )
    invalid_mask = missing_field | missing_table | missing_target
    cleaned = dataframe[~invalid_mask]
    cleaned.to_csv(memory_path, index=False, encoding="utf-8")
    return {
        "path": str(memory_path),
        "before_count": len(dataframe),
        "removed_count": int(invalid_mask.sum()),
        "after_count": len(cleaned),
    }


def clear_stg_field_memory_by_field_key(
    field_key: str,
    path: str | Path | None = None,
) -> dict[str, object]:
    """Remove learned STG records for one normalized field key."""
    normalized_key = stg_field_memory_key(field_key) or str(field_key or "").strip()
    memory_path = Path(path or STG_FIELD_MEMORY_PATH)
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

    dataframe = _read_memory(memory_path)
    remove_mask = dataframe["field_key"].astype(str) == normalized_key
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
        "table_key": stg_table_memory_key(record.source_table_name),
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
        merged = merged.drop_duplicates(subset=["table_key", "field_key"], keep="last")
    merged.to_csv(memory_path, index=False, encoding="utf-8")

    return StgLearningSummary(
        learned_count=len(new_rows),
        memory_count=len(merged),
        output_path=str(memory_path),
    )


def lookup_learned_stg_field(
    source_field_name: str | None,
    memory: pd.DataFrame | None = None,
    *,
    source_table_name: str | None = None,
) -> LearnedStgField | None:
    """Find a learned STG field decision for a source field."""
    return explain_stg_memory_lookup(
        source_field_name,
        memory,
        source_table_name=source_table_name,
    ).learned_field


def explain_stg_memory_lookup(
    source_field_name: str | None,
    memory: pd.DataFrame | None = None,
    *,
    source_table_name: str | None = None,
) -> StgMemoryLookup:
    """Return a learned STG field plus traceable lookup diagnostics."""
    field_key = stg_field_memory_key(source_field_name)
    if not field_key:
        return StgMemoryLookup(
            status="missing_field_key",
            reason="Source field name could not be normalized for STG learning lookup.",
            evidence=("learned_stg_memory=missing_field_key",),
        )
    dataframe = memory if memory is not None else load_stg_field_memory()
    if dataframe is None or dataframe.empty or "field_key" not in dataframe.columns:
        return StgMemoryLookup(
            field_key=field_key,
            table_key=stg_table_memory_key(source_table_name) or None,
            status="memory_unavailable",
            reason="No learned STG memory is available.",
            evidence=(
                "learned_stg_memory=unavailable",
                f"field_key={field_key}",
            ),
        )
    matches = dataframe[dataframe["field_key"].astype(str) == field_key]
    if matches.empty:
        return StgMemoryLookup(
            field_key=field_key,
            table_key=stg_table_memory_key(source_table_name) or None,
            status="not_found",
            reason="No learned STG record matched this field key.",
            evidence=(
                "learned_stg_memory=not_found",
                f"field_key={field_key}",
            ),
        )
    match_scope = "field"
    field_target_count = len(_distinct_targets(matches, "final_stg_field_name"))
    field_record_count = len(matches)
    conflict_count = max(0, field_target_count - 1)
    lookup_table_key = stg_table_memory_key(source_table_name)
    if lookup_table_key:
        table_keys = matches.apply(_row_table_key, axis=1)
        table_matches = matches[table_keys == lookup_table_key]
        if not table_matches.empty:
            matches = table_matches
            match_scope = "table_field"
        elif not _allows_cross_table_reuse(field_key):
            return StgMemoryLookup(
                field_key=field_key,
                table_key=lookup_table_key,
                status="generic_cross_table_blocked",
                reason=(
                    "Learned STG memory exists, but the field key is too generic for "
                    "cross-table reuse."
                ),
                record_count=field_record_count,
                conflict_count=conflict_count,
                evidence=(
                    "learned_stg_memory=blocked_generic_cross_table",
                    f"field_key={field_key}",
                    f"table_key={lookup_table_key}",
                    f"records={field_record_count}",
                ),
            )
        elif field_target_count > 1:
            return StgMemoryLookup(
                field_key=field_key,
                table_key=lookup_table_key,
                status="conflict_cross_table_blocked",
                reason=(
                    "Learned STG memory exists, but this field key has conflicting "
                    "historical targets across tables."
                ),
                record_count=field_record_count,
                conflict_count=conflict_count,
                evidence=(
                    "learned_stg_memory=blocked_conflict_cross_table",
                    f"field_key={field_key}",
                    f"table_key={lookup_table_key}",
                    f"records={field_record_count}",
                    f"conflicts={conflict_count}",
                ),
            )
    row = matches.iloc[-1]
    final_name = str(row.get("final_stg_field_name") or "").strip()
    if not final_name:
        return StgMemoryLookup(
            field_key=field_key,
            table_key=lookup_table_key or None,
            status="invalid_record",
            reason="Learned STG record is missing a final field name.",
            record_count=field_record_count,
            conflict_count=conflict_count,
            evidence=(
                "learned_stg_memory=invalid_record",
                f"field_key={field_key}",
            ),
        )
    final_type = str(row.get("final_data_type") or "").strip() or None
    learned_field = LearnedStgField(
        field_key=field_key,
        final_stg_field_name=final_name,
        final_data_type=final_type,
        table_key=_row_table_key(row) or None,
        match_scope=match_scope,
        conflict_count=conflict_count,
        source=str(row.get("source") or "") or None,
        review_action=str(row.get("review_action") or "") or None,
        reviewed_at=str(row.get("reviewed_at") or "") or None,
    )
    return StgMemoryLookup(
        field_key=field_key,
        table_key=lookup_table_key or None,
        status="matched",
        reason="Learned STG memory matched this field.",
        record_count=field_record_count,
        conflict_count=conflict_count,
        learned_field=learned_field,
        evidence=(
            "learned_stg_memory=matched",
            f"scope={match_scope}",
            f"field_key={field_key}",
            f"table_key={lookup_table_key or 'N/A'}",
            f"records={field_record_count}",
            f"conflicts={conflict_count}",
        ),
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
    recommendation_evidence = dict(payload.get("recommendation_evidence") or {})
    recommendation_evidence.update(
        {
            "mapping_source": "learned_stg_memory",
            "source_category": "learned_review_memory",
            "confidence_score": 1.0,
            "confidence_band": "high",
            "review_reason_codes": ["learned_stg_memory"],
            "action": "rename",
            "recommended_stg_field_name": learned_field.final_stg_field_name,
            "recommended_data_type": (
                learned_field.final_data_type or payload.get("recommended_data_type")
            ),
            "name_changed": (
                payload.get("source_field_name") != learned_field.final_stg_field_name
            ),
        }
    )
    payload["recommendation_evidence"] = recommendation_evidence
    evidence = (
        "learned_from_stg_review_history "
        f"scope={learned_field.match_scope} "
        f"field_key={learned_field.field_key} "
        f"source={learned_field.source or 'review'} "
        f"action={learned_field.review_action or 'unknown'}"
    )
    payload["notes"] = f"{suggestion.notes} {evidence}" if suggestion.notes else evidence
    return StgFieldSuggestion(**payload)

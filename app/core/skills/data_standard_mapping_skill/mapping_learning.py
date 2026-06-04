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
    "table_key",
    "field_key",
    "table_name",
    "field_name",
    "standard_code",
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
    table_key: str | None = None
    match_scope: str = "field"
    conflict_count: int = 0
    source: str | None = None
    review_action: str | None = None
    reviewed_at: str | None = None


@dataclass(frozen=True)
class StandardMappingMemoryLookup:
    """Explainable lookup result for learned standard-mapping memory."""

    field_key: str = ""
    table_key: str | None = None
    status: str = "not_found"
    reason: str = ""
    record_count: int = 0
    conflict_count: int = 0
    learned_mapping: LearnedStandardMapping | None = None
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class StandardMappingMemoryHealth:
    """Health summary for learned standard-mapping memory."""

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


def standard_mapping_memory_key(value: str | None) -> str:
    """Return a normalized field key for standard-mapping memory lookup."""
    tokens = normalize_tokens(expand_tokens(split_tokens(value)))
    return "_".join(tokens)


def table_memory_key(value: str | None) -> str:
    """Return a normalized table key for scoped learned-memory lookup."""
    return standard_mapping_memory_key(value)


def _allows_cross_table_reuse(field_key: str) -> bool:
    tokens = [token for token in field_key.split("_") if token]
    if len(tokens) < 2:
        return False
    return any(token not in GENERIC_FIELD_TOKENS for token in tokens)


def _row_table_key(row: pd.Series) -> str:
    raw_table_key = str(row.get("table_key") or "").strip()
    if raw_table_key:
        return raw_table_key
    return table_memory_key(str(row.get("table_name") or ""))


def _distinct_targets(rows: pd.DataFrame, target_column: str) -> set[str]:
    if target_column not in rows.columns:
        return set()
    return {
        str(value).strip()
        for value in rows[target_column].tolist()
        if str(value or "").strip()
    }


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


def summarize_standard_mapping_memory(
    memory: pd.DataFrame | None = None,
) -> StandardMappingMemoryHealth:
    """Return a maintenance-friendly health summary for mapping memory."""
    dataframe = memory if memory is not None else load_standard_mapping_memory()
    if dataframe is None or dataframe.empty:
        return StandardMappingMemoryHealth()

    prepared = dataframe.copy()
    for column in STANDARD_MAPPING_MEMORY_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None
    prepared = prepared[STANDARD_MAPPING_MEMORY_COLUMNS].astype(object)
    prepared = prepared.where(pd.notna(prepared), None)

    valid_field_rows = prepared[
        prepared["field_key"].map(lambda value: bool(str(value or "").strip()))
    ]
    valid_target_rows = valid_field_rows[
        valid_field_rows["standard_code"].map(lambda value: bool(str(value or "").strip()))
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
        if len(_distinct_targets(group, "standard_code")) > 1:
            conflict_field_keys.append(field_key_text)

    invalid_record_keys = sorted(
        {
            f"{row.get('table_key') or 'missing_table'}:{row.get('field_key') or 'missing_field'}"
            for _, row in invalid_rows.iterrows()
        }
    )

    return StandardMappingMemoryHealth(
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


def standard_mapping_memory_details(
    memory: pd.DataFrame | None = None,
) -> dict[str, object]:
    """Return conflict, generic, and invalid learned mapping records."""
    dataframe = memory if memory is not None else load_standard_mapping_memory()
    if dataframe is None or dataframe.empty:
        return {
            "conflict_records": [],
            "generic_records": [],
            "invalid_records": [],
        }

    prepared = dataframe.copy()
    for column in STANDARD_MAPPING_MEMORY_COLUMNS:
        if column not in prepared.columns:
            prepared[column] = None
    prepared = prepared[STANDARD_MAPPING_MEMORY_COLUMNS].astype(object)
    prepared = prepared.where(pd.notna(prepared), None)

    missing_field = ~prepared["field_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_table = ~prepared["table_key"].map(
        lambda value: bool(str(value or "").strip())
    )
    missing_target = ~prepared["standard_code"].map(
        lambda value: bool(str(value or "").strip())
    )
    invalid_rows = prepared[missing_field | missing_table | missing_target]
    valid_rows = prepared[~missing_field & ~missing_target]

    conflict_field_keys = {
        str(field_key)
        for field_key, group in valid_rows.groupby("field_key")
        if len(_distinct_targets(group, "standard_code")) > 1
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


def prune_invalid_standard_mapping_memory(
    path: str | Path | None = None,
) -> dict[str, object]:
    """Remove invalid learned mapping records from local memory."""
    memory_path = Path(path or STANDARD_MAPPING_MEMORY_PATH)
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
    missing_target = ~dataframe["standard_code"].map(
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


def clear_standard_mapping_memory_by_field_key(
    field_key: str,
    path: str | Path | None = None,
) -> dict[str, object]:
    """Remove learned mapping records for one normalized field key."""
    normalized_key = standard_mapping_memory_key(field_key) or str(field_key or "").strip()
    memory_path = Path(path or STANDARD_MAPPING_MEMORY_PATH)
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


def _record_to_memory_row(record: MappingReviewRecord) -> dict[str, object] | None:
    if record.review_action not in LEARNABLE_REVIEW_ACTIONS:
        return None
    if not record.final_standard_code:
        return None
    field_key = standard_mapping_memory_key(record.field_name)
    if not field_key:
        return None
    return {
        "table_key": table_memory_key(record.table_name),
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
        merged = merged.drop_duplicates(subset=["table_key", "field_key"], keep="last")
    merged.to_csv(memory_path, index=False, encoding="utf-8")

    return StandardMappingLearningSummary(
        learned_count=len(new_rows),
        memory_count=len(merged),
        output_path=str(memory_path),
    )


def lookup_learned_standard_mapping(
    field_name: str | None,
    memory: pd.DataFrame | None = None,
    *,
    table_name: str | None = None,
) -> LearnedStandardMapping | None:
    """Find a learned standard mapping for a field name."""
    return explain_standard_mapping_memory_lookup(
        field_name,
        memory,
        table_name=table_name,
    ).learned_mapping


def explain_standard_mapping_memory_lookup(
    field_name: str | None,
    memory: pd.DataFrame | None = None,
    *,
    table_name: str | None = None,
) -> StandardMappingMemoryLookup:
    """Return a learned standard mapping plus traceable lookup diagnostics."""
    field_key = standard_mapping_memory_key(field_name)
    if not field_key:
        return StandardMappingMemoryLookup(
            status="missing_field_key",
            reason="Field name could not be normalized for learning lookup.",
            evidence=("learned_mapping_memory=missing_field_key",),
        )
    dataframe = memory if memory is not None else load_standard_mapping_memory()
    if dataframe is None or dataframe.empty or "field_key" not in dataframe.columns:
        return StandardMappingMemoryLookup(
            field_key=field_key,
            table_key=table_memory_key(table_name) or None,
            status="memory_unavailable",
            reason="No learned mapping memory is available.",
            evidence=(
                "learned_mapping_memory=unavailable",
                f"field_key={field_key}",
            ),
        )
    matches = dataframe[dataframe["field_key"].astype(str) == field_key]
    if matches.empty:
        return StandardMappingMemoryLookup(
            field_key=field_key,
            table_key=table_memory_key(table_name) or None,
            status="not_found",
            reason="No learned mapping record matched this field key.",
            evidence=(
                "learned_mapping_memory=not_found",
                f"field_key={field_key}",
            ),
        )
    match_scope = "field"
    field_target_count = len(_distinct_targets(matches, "standard_code"))
    field_record_count = len(matches)
    conflict_count = max(0, field_target_count - 1)
    lookup_table_key = table_memory_key(table_name)
    if lookup_table_key:
        table_keys = matches.apply(_row_table_key, axis=1)
        table_matches = matches[table_keys == lookup_table_key]
        if not table_matches.empty:
            matches = table_matches
            match_scope = "table_field"
        elif not _allows_cross_table_reuse(field_key):
            return StandardMappingMemoryLookup(
                field_key=field_key,
                table_key=lookup_table_key,
                status="generic_cross_table_blocked",
                reason=(
                    "Learned mapping exists, but the field key is too generic for "
                    "cross-table reuse."
                ),
                record_count=field_record_count,
                conflict_count=conflict_count,
                evidence=(
                    "learned_mapping_memory=blocked_generic_cross_table",
                    f"field_key={field_key}",
                    f"table_key={lookup_table_key}",
                    f"records={field_record_count}",
                ),
            )
        elif field_target_count > 1:
            return StandardMappingMemoryLookup(
                field_key=field_key,
                table_key=lookup_table_key,
                status="conflict_cross_table_blocked",
                reason=(
                    "Learned mapping exists, but this field key has conflicting "
                    "historical targets across tables."
                ),
                record_count=field_record_count,
                conflict_count=conflict_count,
                evidence=(
                    "learned_mapping_memory=blocked_conflict_cross_table",
                    f"field_key={field_key}",
                    f"table_key={lookup_table_key}",
                    f"records={field_record_count}",
                    f"conflicts={conflict_count}",
                ),
            )
    row = matches.iloc[-1]
    standard_code = str(row.get("standard_code") or "").strip()
    if not standard_code:
        return StandardMappingMemoryLookup(
            field_key=field_key,
            table_key=lookup_table_key or None,
            status="invalid_record",
            reason="Learned mapping record is missing a standard code.",
            record_count=field_record_count,
            conflict_count=conflict_count,
            evidence=(
                "learned_mapping_memory=invalid_record",
                f"field_key={field_key}",
            ),
        )
    learned_mapping = LearnedStandardMapping(
        field_key=field_key,
        standard_code=standard_code,
        table_key=_row_table_key(row) or None,
        match_scope=match_scope,
        conflict_count=conflict_count,
        source=str(row.get("source") or "") or None,
        review_action=str(row.get("review_action") or "") or None,
        reviewed_at=str(row.get("reviewed_at") or "") or None,
    )
    return StandardMappingMemoryLookup(
        field_key=field_key,
        table_key=lookup_table_key or None,
        status="matched",
        reason="Learned mapping memory matched this field.",
        record_count=field_record_count,
        conflict_count=conflict_count,
        learned_mapping=learned_mapping,
        evidence=(
            "learned_mapping_memory=matched",
            f"scope={match_scope}",
            f"field_key={field_key}",
            f"table_key={lookup_table_key or 'N/A'}",
            f"records={field_record_count}",
            f"conflicts={conflict_count}",
        ),
    )

"""Local CSV-backed storage for quality rule review overrides."""

import json
from pathlib import Path

import pandas as pd

from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_compact

PROJECT_ROOT = Path(__file__).resolve().parents[3]
OVERRIDES_DIR = PROJECT_ROOT / "app" / "data" / "overrides"
REVIEW_HISTORY_DIR = PROJECT_ROOT / "app" / "data" / "review_history"
QUALITY_RULE_SESSIONS_DIR = REVIEW_HISTORY_DIR / "quality_rule_sessions"
QUALITY_RULE_OVERRIDES_PATH = OVERRIDES_DIR / "quality_rule_overrides.csv"

QUALITY_RULE_OVERRIDE_COLUMNS = [
    "source_table_name",
    "source_field_name",
    "rule_name",
    "rule_description",
    "rule_scope",
    "field_group",
    "target_table_name",
    "target_field_name",
    "rule_type",
    "original_rule_expression",
    "final_rule_expression",
    "original_severity",
    "final_severity",
    "risk_level",
    "recommended_field_name",
    "recommendation_source",
    "match_basis",
    "export_formats",
    "learning_context",
    "review_action",
    "confidence",
    "review_priority",
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


def _write_csv(path: Path, records: list[dict[str, object]]) -> str:
    ensure_directory(path.parent)
    normalized_records = []
    for record in records:
        payload = dict(record)
        field_group = payload.get("field_group")
        if isinstance(field_group, list):
            payload["field_group"] = json.dumps(field_group, ensure_ascii=False)
        learning_context = payload.get("learning_context")
        if isinstance(learning_context, list):
            payload["learning_context"] = json.dumps(learning_context, ensure_ascii=False)
        export_formats = payload.get("export_formats")
        if isinstance(export_formats, list):
            payload["export_formats"] = json.dumps(export_formats, ensure_ascii=False)
        normalized_records.append(payload)
    dataframe = pd.DataFrame(normalized_records, columns=QUALITY_RULE_OVERRIDE_COLUMNS)
    dataframe.to_csv(path, index=False, encoding="utf-8")
    return str(path)


def _parse_field_group(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return [item.strip() for item in text.split("|") if item.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return []


def _parse_learning_context(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return [item.strip() for item in text.split("|") if item.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return []


def _parse_export_formats(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        return [item.strip() for item in text.split("|") if item.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if str(item).strip()]
    return []


def _merge_by_key(
    existing_records: list[dict[str, object]],
    new_records: list[dict[str, object]],
) -> list[dict[str, object]]:
    merged: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for record in existing_records + new_records:
        field_group = _parse_field_group(record.get("field_group"))
        key = (
            str(record.get("source_table_name", "") or ""),
            str(record.get("rule_scope", "field") or "field"),
            "|".join(sorted(field_group))
            or str(record.get("source_field_name", "") or ""),
            str(record.get("rule_type", "") or ""),
        )
        merged[key] = record
    return list(merged.values())


def _save_review_session_snapshot(records: list[dict[str, object]]) -> str:
    ensure_directory(QUALITY_RULE_SESSIONS_DIR)
    timestamp = utc_now_compact()
    session_path = QUALITY_RULE_SESSIONS_DIR / f"quality_rule_review_{timestamp}.json"
    session_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(session_path)


def build_quality_rule_key(
    source_table_name: str,
    source_field_name: str,
    rule_type: str,
    rule_scope: str = "field",
    field_group: list[str] | None = None,
) -> str:
    """Build the stable lookup key for one quality rule review record."""
    normalized_scope = str(rule_scope or "field").strip() or "field"
    group_key = "|".join(sorted(str(item) for item in field_group or [] if str(item).strip()))
    field_key = group_key or source_field_name
    return f"{source_table_name}.{normalized_scope}.{field_key}.{rule_type}"


def load_quality_rule_overrides() -> list[QualityRuleReviewRecord]:
    """Load locally persisted quality rule overrides."""
    dataframe = _read_csv(QUALITY_RULE_OVERRIDES_PATH, QUALITY_RULE_OVERRIDE_COLUMNS)
    records = []
    for row in dataframe.to_dict("records"):
        payload = dict(row)
        payload["rule_scope"] = payload.get("rule_scope") or "field"
        payload["field_group"] = _parse_field_group(payload.get("field_group"))
        payload["learning_context"] = _parse_learning_context(
            payload.get("learning_context")
        )
        payload["export_formats"] = _parse_export_formats(
            payload.get("export_formats")
        )
        records.append(QualityRuleReviewRecord(**payload))
    return records


def save_quality_rule_review_records(
    records: list[QualityRuleReviewRecord],
) -> dict[str, str | int]:
    """Persist quality rule review records and write a session snapshot."""
    new_records = [record.model_dump() for record in records]
    existing_records = [record.model_dump() for record in load_quality_rule_overrides()]
    merged = _merge_by_key(existing_records, new_records)
    csv_path = _write_csv(QUALITY_RULE_OVERRIDES_PATH, merged)
    history_path = _save_review_session_snapshot(new_records)
    from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
        clear_quality_rule_learning_caches,
    )

    clear_quality_rule_learning_caches()
    return {"path": csv_path, "history_path": history_path, "saved_count": len(records)}


def build_quality_rule_override_lookup(
    records: list[QualityRuleReviewRecord] | None = None,
) -> dict[str, QualityRuleReviewRecord]:
    """Build a lookup for quality rule overrides by table, field, and rule type."""
    records = records if records is not None else load_quality_rule_overrides()
    lookup: dict[str, QualityRuleReviewRecord] = {}
    for record in records:
        key = build_quality_rule_key(
            record.source_table_name,
            record.source_field_name,
            record.rule_type,
            rule_scope=record.rule_scope,
            field_group=record.field_group,
        )
        lookup[key] = record
        legacy_key = (
            f"{record.source_table_name}.{record.source_field_name}.{record.rule_type}"
        )
        lookup.setdefault(legacy_key, record)
    return lookup


# TODO: move quality rule override storage behind a repository interface when multi-user review is introduced.

"""Review provenance helpers for detecting stale replay decisions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STANDARD_FIELDS_PATH = PROJECT_ROOT / "app" / "data" / "standards" / "standard_fields.csv"
CONFIG_ROOT = PROJECT_ROOT / "app" / "config"


def stable_hash(payload: object) -> str:
    """Return a stable SHA-256 hash for JSON-serializable provenance payloads."""
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_content_hash(path: Path) -> str:
    if not path.exists():
        return stable_hash({"missing": str(path)})
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_fingerprint() -> str:
    entries: list[dict[str, str]] = []
    if CONFIG_ROOT.exists():
        for path in sorted(CONFIG_ROOT.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json"}:
                entries.append(
                    {
                        "path": str(path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
                        "hash": file_content_hash(path),
                    }
                )
    return stable_hash(entries)


def standard_set_version() -> str:
    return file_content_hash(STANDARD_FIELDS_PATH)


def dictionary_version() -> str:
    return config_fingerprint()


def mapping_source_field_hash(result: MappingResult) -> str:
    return stable_hash(
        {
            "table_name": result.table_name,
            "field_name": result.field_name,
            "context_evidence": result.context_evidence,
            "recommended_standard_code": result.recommended_standard_code,
            "recommended_standard_name": result.recommended_standard_name,
            "recommended_standard_name_cn": result.recommended_standard_name_cn,
        }
    )


def stg_source_field_hash(suggestion: StgFieldSuggestion) -> str:
    return stable_hash(
        {
            "source_table_name": suggestion.source_table_name,
            "source_field_name": suggestion.source_field_name,
            "source_field_name_cn": suggestion.source_field_name_cn,
            "source_data_type": suggestion.source_data_type,
            "recommended_stg_field_name": suggestion.recommended_stg_field_name,
            "recommended_data_type": suggestion.recommended_data_type,
            "nullable": suggestion.nullable,
        }
    )


def quality_rule_source_hash(suggestion: QualityRuleSuggestion) -> str:
    return stable_hash(
        {
            "source_table_name": suggestion.source_table_name,
            "source_field_name": suggestion.source_field_name,
            "rule_name": suggestion.rule_name,
            "rule_scope": suggestion.rule_scope,
            "field_group": suggestion.field_group,
            "target_table_name": suggestion.target_table_name,
            "target_field_name": suggestion.target_field_name,
            "rule_type": suggestion.rule_type,
            "rule_expression": suggestion.rule_expression,
            "severity": suggestion.severity,
            "recommendation_source": suggestion.recommendation_source,
            "match_basis": suggestion.match_basis,
        }
    )


def review_provenance(source_field_hash: str) -> dict[str, str]:
    return {
        "dictionary_version": dictionary_version(),
        "standard_set_version": standard_set_version(),
        "config_fingerprint": config_fingerprint(),
        "source_field_hash": source_field_hash,
    }


def mapping_review_provenance(result: MappingResult) -> dict[str, str]:
    return review_provenance(mapping_source_field_hash(result))


def stg_review_provenance(suggestion: StgFieldSuggestion) -> dict[str, str]:
    return review_provenance(stg_source_field_hash(suggestion))


def quality_rule_review_provenance(
    suggestion: QualityRuleSuggestion,
) -> dict[str, str]:
    return review_provenance(quality_rule_source_hash(suggestion))


def stale_provenance_fields(
    record: Any,
    current_provenance: dict[str, str],
) -> list[str]:
    stale_fields: list[str] = []
    for field_name, current_value in current_provenance.items():
        recorded_value = getattr(record, field_name, None)
        if recorded_value and recorded_value != current_value:
            stale_fields.append(field_name)
    return stale_fields

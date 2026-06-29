"""Pure helpers for collecting Streamlit review form inputs."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

SessionValueGetter = Callable[[str], Any | None]


def candidate_evidence(top_candidates: Iterable[dict[str, object]]) -> list[str]:
    """Format mapping candidate evidence for review explanation blocks."""
    evidence: list[str] = []
    for candidate in top_candidates:
        standard_code = candidate.get("standard_code") or "N/A"
        standard_name = candidate.get("standard_name") or "N/A"
        match_score = candidate.get("match_score")
        match_reason = candidate.get("match_reason") or "N/A"
        line = f"{standard_code} | {standard_name} | 分数={match_score} | {match_reason}"
        if candidate.get("risk_hint"):
            line = f"{line} | 风险={candidate['risk_hint']}"
        if candidate.get("action_suggestion"):
            line = f"{line} | 建议={candidate['action_suggestion']}"
        evidence.append(line)
    return evidence


def collect_mapping_review_inputs(
    mapping_results: Iterable[Any],
    get_value: SessionValueGetter,
) -> dict[str, dict[str, Any | None]]:
    """Collect mapping review widget values keyed by table and field."""
    return {
        f"{item.table_name}.{item.field_name}": {
            "review_action": get_value(f"mapping_action_{item.table_name}.{item.field_name}"),
            "final_standard_code": get_value(
                f"mapping_final_{item.table_name}.{item.field_name}"
            ),
            "reviewer_note": get_value(f"mapping_note_{item.table_name}.{item.field_name}"),
        }
        for item in mapping_results
    }


def collect_stg_review_inputs(
    stg_suggestions: Iterable[Any],
    get_value: SessionValueGetter,
) -> dict[str, dict[str, Any | None]]:
    """Collect STG review widget values keyed by source table and field."""
    return {
        f"{item.source_table_name}.{item.source_field_name}": {
            "review_action": get_value(
                f"stg_action_{item.source_table_name}.{item.source_field_name}"
            ),
            "final_stg_field_name": get_value(
                f"stg_final_name_{item.source_table_name}.{item.source_field_name}"
            ),
            "final_data_type": get_value(
                f"stg_final_type_{item.source_table_name}.{item.source_field_name}"
            ),
            "reviewer_note": get_value(
                f"stg_note_{item.source_table_name}.{item.source_field_name}"
            ),
        }
        for item in stg_suggestions
    }


def collect_quality_review_inputs(
    rules: Iterable[Any],
    key_for_rule: Callable[[Any], str],
    get_value: SessionValueGetter,
) -> dict[str, dict[str, Any | None]]:
    """Collect quality-rule review widget values keyed by rule identity."""
    review_inputs: dict[str, dict[str, Any | None]] = {}
    for rule in rules:
        key = key_for_rule(rule)
        review_inputs[key] = {
            "review_action": get_value(f"quality_action_{key}"),
            "final_rule_expression": get_value(f"quality_expression_{key}"),
            "final_severity": get_value(f"quality_severity_{key}"),
            "reviewer_note": get_value(f"quality_note_{key}"),
        }
    return review_inputs

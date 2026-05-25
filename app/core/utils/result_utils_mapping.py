"""Mapping and STG dataframe helpers."""

import pandas as pd

from app.core.models.mapping_result import MappingResult, UnmappedField
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_table_suggestion import StgTableSuggestion


def mapping_results_to_dataframe(mapping_results: list[MappingResult]) -> pd.DataFrame:
    """Convert mapping recommendations to a stable dataframe."""
    records = []
    for result in mapping_results:
        records.append(
            {
                "table_name": result.table_name,
                "field_name": result.field_name,
                "recommended_standard_code": result.recommended_standard_code,
                "recommended_standard_name": result.recommended_standard_name,
                "recommended_standard_name_cn": result.recommended_standard_name_cn,
                "match_score": result.match_score,
                "match_reason": result.match_reason,
                "risk_hint": result.risk_hint,
                "action_suggestion": result.action_suggestion,
                "requires_manual_review": result.requires_manual_review,
                "mapping_status": result.mapping_status,
                "context_evidence_joined": " | ".join(result.context_evidence),
                "candidate_count": result.candidate_count,
                "confirmed_source": result.confirmed_source,
                "review_action": result.review_action,
                "reviewer_note": result.reviewer_note,
            }
        )
    return pd.DataFrame(records)


def unmapped_fields_to_dataframe(unmapped_fields: list[UnmappedField]) -> pd.DataFrame:
    """Convert unmapped or low-confidence fields to a stable dataframe."""
    records = []
    for field in unmapped_fields:
        records.append(
            {
                "table_name": field.table_name,
                "field_name": field.field_name,
                "field_name_cn": field.field_name_cn,
                "best_candidate_code": field.best_candidate_code,
                "best_candidate_score": field.best_candidate_score,
                "reason": field.reason,
                "risk_hint": field.risk_hint,
                "action_suggestion": field.action_suggestion,
                "requires_manual_review": field.requires_manual_review,
                "evidence_joined": " | ".join(field.evidence),
            }
        )
    return pd.DataFrame(records)


def stg_tables_to_dataframe(
    stg_suggestions: list[StgTableSuggestion],
) -> pd.DataFrame:
    """Convert STG table suggestions to a stable dataframe."""
    records = []
    for suggestion in stg_suggestions:
        records.append(
            {
                "source_table_name": suggestion.source_table_name,
                "recommended_stg_table_name": suggestion.recommended_stg_table_name,
                "recommended_stg_table_name_cn": suggestion.recommended_stg_table_name_cn,
                "summary": suggestion.summary,
                "issue_flags_joined": ", ".join(suggestion.issue_flags),
            }
        )
    return pd.DataFrame(records)


def stg_fields_to_dataframe(
    stg_field_suggestions: list[StgFieldSuggestion],
) -> pd.DataFrame:
    """Convert STG field suggestions to a stable dataframe."""
    records = []
    for suggestion in stg_field_suggestions:
        records.append(
            {
                "source_table_name": suggestion.source_table_name,
                "source_field_name": suggestion.source_field_name,
                "source_field_name_cn": suggestion.source_field_name_cn,
                "source_data_type": suggestion.source_data_type,
                "recommended_stg_field_name": suggestion.recommended_stg_field_name,
                "recommended_stg_field_name_cn": suggestion.recommended_stg_field_name_cn,
                "recommended_data_type": suggestion.recommended_data_type,
                "nullable": suggestion.nullable,
                "mapping_source": suggestion.mapping_source,
                "match_score": suggestion.match_score,
                "action": suggestion.action,
                "notes": suggestion.notes,
                "confirmed_source": suggestion.confirmed_source,
                "review_action": suggestion.review_action,
                "reviewer_note": suggestion.reviewer_note,
            }
        )
    return pd.DataFrame(records)

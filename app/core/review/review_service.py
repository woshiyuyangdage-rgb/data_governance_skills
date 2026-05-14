"""Helpers for building, applying, and summarizing human review results."""

from collections import Counter

from app.core.knowledge.knowledge_loader import load_standard_fields
from app.core.models.mapping_result import MappingResult
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.review_summary import ReviewSummary
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.stg_review_record import StgReviewRecord
from app.core.review.override_store import (
    build_mapping_override_lookup,
    build_stg_override_lookup,
)
from app.core.utils.time_utils import utc_now_seconds


def _utc_now() -> str:
    return utc_now_seconds()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _mapping_standard_lookup() -> dict[str, dict[str, str | None]]:
    dataframe = load_standard_fields()
    lookup: dict[str, dict[str, str | None]] = {}
    for _, row in dataframe.iterrows():
        standard_code = str(row["standard_code"]).strip()
        lookup[standard_code] = {
            "standard_name": str(row["standard_name"]).strip(),
            "standard_name_cn": (
                None
                if str(row["standard_name_cn"]).strip().lower() == "nan"
                else str(row["standard_name_cn"]).strip()
            ),
        }
    return lookup


def build_mapping_review_records_from_results(
    mapping_results: list[MappingResult],
    review_inputs: dict[str, dict[str, str | None]] | None = None,
    source: str = "review_workbench",
) -> list[MappingReviewRecord]:
    """Convert mapping results and user review inputs into persistable records."""
    review_inputs = review_inputs or {}
    records: list[MappingReviewRecord] = []

    for result in mapping_results:
        key = f"{result.table_name}.{result.field_name}"
        user_input = review_inputs.get(key, {})
        action = str(user_input.get("review_action") or "accept")
        final_standard_code = _normalize_optional_text(
            user_input.get("final_standard_code")
        )
        if action == "accept":
            final_standard_code = result.recommended_standard_code
        elif action in {"reject", "mark_for_manual_review"} and not final_standard_code:
            final_standard_code = result.recommended_standard_code

        records.append(
            MappingReviewRecord(
                table_name=result.table_name,
                field_name=result.field_name,
                original_recommended_standard_code=result.recommended_standard_code,
                final_standard_code=final_standard_code,
                review_action=action,
                reviewer_note=_normalize_optional_text(user_input.get("reviewer_note")),
                reviewed_at=_utc_now(),
                source=source,
            )
        )

    return records


def build_stg_review_records_from_results(
    stg_suggestions: list[StgFieldSuggestion],
    review_inputs: dict[str, dict[str, str | None]] | None = None,
    source: str = "review_workbench",
) -> list[StgReviewRecord]:
    """Convert STG suggestions and user review inputs into persistable records."""
    review_inputs = review_inputs or {}
    records: list[StgReviewRecord] = []

    for suggestion in stg_suggestions:
        key = f"{suggestion.source_table_name}.{suggestion.source_field_name}"
        user_input = review_inputs.get(key, {})
        action = str(user_input.get("review_action") or "accept")
        final_stg_field_name = _normalize_optional_text(
            user_input.get("final_stg_field_name")
        )
        final_data_type = _normalize_optional_text(user_input.get("final_data_type"))

        if action == "accept":
            final_stg_field_name = suggestion.recommended_stg_field_name
            final_data_type = suggestion.recommended_data_type
        elif action in {"reject", "mark_for_manual_review"}:
            final_stg_field_name = (
                final_stg_field_name or suggestion.recommended_stg_field_name
            )
            final_data_type = final_data_type or suggestion.recommended_data_type

        records.append(
            StgReviewRecord(
                source_table_name=suggestion.source_table_name,
                source_field_name=suggestion.source_field_name,
                original_recommended_stg_field_name=suggestion.recommended_stg_field_name,
                final_stg_field_name=final_stg_field_name,
                original_recommended_data_type=suggestion.recommended_data_type,
                final_data_type=final_data_type,
                review_action=action,
                reviewer_note=_normalize_optional_text(user_input.get("reviewer_note")),
                reviewed_at=_utc_now(),
                source=source,
            )
        )

    return records


def summarize_review_records(
    mapping_records: list[MappingReviewRecord] | None = None,
    stg_records: list[StgReviewRecord] | None = None,
) -> ReviewSummary:
    """Aggregate review action counts across mapping and STG records."""
    action_counter: Counter[str] = Counter()
    total_reviewed_count = 0

    for record in (mapping_records or []) + (stg_records or []):
        action_counter[record.review_action] += 1
        total_reviewed_count += 1

    return ReviewSummary(
        accepted_count=action_counter.get("accept", 0),
        rejected_count=action_counter.get("reject", 0),
        edited_count=action_counter.get("edit", 0),
        manual_review_count=action_counter.get("mark_for_manual_review", 0),
        total_reviewed_count=total_reviewed_count,
    )


def apply_mapping_overrides_to_results(
    mapping_results: list[MappingResult],
    override_records: list[MappingReviewRecord] | None = None,
) -> tuple[list[MappingResult], int, ReviewSummary]:
    """Apply saved mapping overrides to current mapping results."""
    standard_lookup = _mapping_standard_lookup()
    override_lookup = build_mapping_override_lookup(override_records)
    applied_records: list[MappingReviewRecord] = []
    confirmed_results: list[MappingResult] = []
    applied_count = 0

    for result in mapping_results:
        key = f"{result.table_name}.{result.field_name}"
        override = override_lookup.get(key)
        if override is None:
            confirmed_results.append(result)
            continue

        applied_count += 1
        applied_records.append(override)
        base_payload = result.model_dump()
        action = override.review_action

        if action == "accept":
            base_payload["match_reason"] = (
                f"{result.match_reason}; override accept applied"
                if result.match_reason
                else "override accept applied"
            )
            base_payload["confirmed_source"] = "override_accept"
        elif action == "edit":
            standard_code = override.final_standard_code
            standard_info = standard_lookup.get(standard_code or "", {})
            base_payload["recommended_standard_code"] = standard_code
            base_payload["recommended_standard_name"] = (
                standard_info.get("standard_name") or standard_code
            )
            base_payload["recommended_standard_name_cn"] = standard_info.get(
                "standard_name_cn"
            )
            base_payload["match_reason"] = (
                f"{result.match_reason}; override edit applied"
                if result.match_reason
                else "override edit applied"
            )
            base_payload["confirmed_source"] = "override_edit"
        elif action == "reject":
            base_payload["recommended_standard_code"] = None
            base_payload["recommended_standard_name"] = None
            base_payload["recommended_standard_name_cn"] = None
            base_payload["match_score"] = 0.0
            base_payload["match_reason"] = "override reject applied"
            base_payload["confirmed_source"] = "override_reject"
        elif action == "mark_for_manual_review":
            base_payload["match_reason"] = (
                f"{result.match_reason}; marked for manual review"
                if result.match_reason
                else "marked for manual review"
            )
            base_payload["confirmed_source"] = "override_manual_review"

        base_payload["review_action"] = action
        base_payload["reviewer_note"] = override.reviewer_note
        confirmed_results.append(MappingResult(**base_payload))

    return confirmed_results, applied_count, summarize_review_records(applied_records, [])


def apply_stg_overrides_to_suggestions(
    stg_suggestions: list[StgFieldSuggestion],
    override_records: list[StgReviewRecord] | None = None,
) -> tuple[list[StgFieldSuggestion], int, ReviewSummary]:
    """Apply saved STG overrides to current STG suggestions."""
    override_lookup = build_stg_override_lookup(override_records)
    applied_records: list[StgReviewRecord] = []
    confirmed_suggestions: list[StgFieldSuggestion] = []
    applied_count = 0

    for suggestion in stg_suggestions:
        key = f"{suggestion.source_table_name}.{suggestion.source_field_name}"
        override = override_lookup.get(key)
        if override is None:
            confirmed_suggestions.append(suggestion)
            continue

        applied_count += 1
        applied_records.append(override)
        base_payload = suggestion.model_dump()
        action = override.review_action

        if action == "accept":
            base_payload["notes"] = (
                f"{suggestion.notes} Override accept applied."
                if suggestion.notes
                else "Override accept applied."
            )
            base_payload["confirmed_source"] = "override_accept"
        elif action == "edit":
            base_payload["recommended_stg_field_name"] = (
                override.final_stg_field_name or suggestion.recommended_stg_field_name
            )
            base_payload["recommended_data_type"] = (
                override.final_data_type or suggestion.recommended_data_type
            )
            base_payload["notes"] = (
                f"{suggestion.notes} Override edit applied."
                if suggestion.notes
                else "Override edit applied."
            )
            base_payload["confirmed_source"] = "override_edit"
        elif action == "reject":
            base_payload["action"] = "manual_review_required"
            base_payload["notes"] = (
                f"{suggestion.notes} Override reject applied."
                if suggestion.notes
                else "Override reject applied."
            )
            base_payload["confirmed_source"] = "override_reject"
        elif action == "mark_for_manual_review":
            base_payload["action"] = "manual_review_required"
            base_payload["notes"] = (
                f"{suggestion.notes} Marked for manual review."
                if suggestion.notes
                else "Marked for manual review."
            )
            base_payload["confirmed_source"] = "override_manual_review"

        base_payload["review_action"] = action
        base_payload["reviewer_note"] = override.reviewer_note
        confirmed_suggestions.append(StgFieldSuggestion(**base_payload))

    return confirmed_suggestions, applied_count, summarize_review_records([], applied_records)


# TODO: extend review application with richer scope rules, multi-user history, and future agent-readable decision retrieval.

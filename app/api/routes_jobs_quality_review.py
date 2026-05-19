"""Review-oriented quality job routes."""

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    MappingReviewSaveRequest,
    QualityRuleReviewRequest,
    StgReviewSaveRequest,
)
from app.core.models.review_summary import ReviewSummary
from app.core.review.override_store import (
    load_mapping_overrides,
    load_stg_overrides,
    save_mapping_review_records,
    save_stg_review_records,
)
from app.core.review.quality_override_store import save_quality_rule_review_records
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.review.review_service import summarize_review_records
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill

router = APIRouter()


@router.post("/save-mapping-review")
def save_mapping_review(payload: MappingReviewSaveRequest) -> dict[str, object]:
    """Save mapping review records to local override storage."""
    result = save_mapping_review_records(payload.records)
    return {
        "message": "Mapping review records were saved successfully.",
        "saved_count": result["saved_count"],
        "path": result["path"],
        "history_path": result["history_path"],
    }


@router.post("/save-stg-review")
def save_stg_review(payload: StgReviewSaveRequest) -> dict[str, object]:
    """Save STG review records to local override storage."""
    result = save_stg_review_records(payload.records)
    return {
        "message": "STG review records were saved successfully.",
        "saved_count": result["saved_count"],
        "path": result["path"],
        "history_path": result["history_path"],
    }


@router.get("/list-review-summary", response_model=ReviewSummary)
def list_review_summary() -> ReviewSummary:
    """Return aggregated counts from locally stored review overrides."""
    return summarize_review_records(load_mapping_overrides(), load_stg_overrides())


@router.post("/review-quality-rules")
def review_quality_rules_route(payload: QualityRuleReviewRequest) -> dict[str, object]:
    """Review quality rule suggestions and build confirmed quality rules."""
    try:
        suggestions = list(payload.quality_rule_suggestions)
        cross_field_rules = list(payload.cross_field_quality_rules)
        if not suggestions and payload.workflow_result is not None:
            suggestions = list(payload.workflow_result.quality_rule_suggestions)
        if not cross_field_rules and payload.workflow_result is not None:
            cross_field_rules = list(payload.workflow_result.cross_field_quality_rules)
        suggestions = suggestions + [
            QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
            for rule in cross_field_rules
        ]
        if not suggestions:
            raise ValueError(
                "quality_rule_suggestions, cross_field_quality_rules, or workflow_result suggestions are required."
            )

        records = list(payload.records)
        if not records:
            records = build_quality_rule_review_records_from_results(
                suggestions,
                payload.review_inputs,
                source=payload.source,
            )

        reviewed_suggestions, applied_count, _ = apply_quality_rule_overrides_to_results(
            suggestions,
            records,
        )
        confirmed_rules = build_confirmed_quality_rules(suggestions, records)
        summary = summarize_quality_rule_review_records(
            records,
            confirmed_count=len(confirmed_rules),
        )
        saved_payload = (
            save_quality_rule_review_records(records) if payload.save_overrides else None
        )
        return {
            "message": "Quality rules were reviewed successfully.",
            "review_records": [record.model_dump() for record in records],
            "reviewed_quality_rule_suggestions": [
                suggestion.model_dump() for suggestion in reviewed_suggestions
            ],
            "confirmed_quality_rules": [rule.model_dump() for rule in confirmed_rules],
            "quality_rule_review_summary": summary,
            "applied_quality_review_count": applied_count,
            "saved": saved_payload,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

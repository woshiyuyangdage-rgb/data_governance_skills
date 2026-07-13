"""Confirmed quality-rule export job routes."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.job_requests import ConfirmedQualityRuleExportRequest
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.rule_export_result import RuleExportResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.review.quality_review_service import build_confirmed_quality_rules
from app.core.skills.data_quality_rule_skill import QualityRuleRecommendationSkill
from app.core.utils.file_utils import resolve_allowed_local_path

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@router.post("/export-confirmed-quality-rules")
def export_confirmed_quality_rules_route(
    payload: ConfirmedQualityRuleExportRequest,
) -> dict[str, object]:
    """Export confirmed quality rules as JSON or dbt YAML."""
    try:
        confirmed_rules = list(payload.confirmed_quality_rules)
        workflow_result = payload.workflow_result
        if not confirmed_rules and workflow_result is not None:
            confirmed_rules = list(workflow_result.confirmed_quality_rules)

        if not confirmed_rules and payload.file_path:
            workflow_result = (
                run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
                    payload.file_path
                )
                if payload.apply_review_replay
                else run_p0_plus_mapping_plus_stg_plus_quality_from_file(
                    payload.file_path
                )
            )
            confirmed_rules = list(workflow_result.confirmed_quality_rules)
            if not confirmed_rules and payload.apply_review_replay:
                review_queue = list(workflow_result.quality_rule_suggestions) + [
                    QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
                    for rule in workflow_result.cross_field_quality_rules
                ]
                confirmed_rules = build_confirmed_quality_rules(
                    review_queue,
                    load_quality_rule_overrides(),
                )

        output_dir = resolve_allowed_local_path(
            payload.output_dir or PROJECT_ROOT / "outputs" / "rule_exports",
            path_label="output_dir",
        )
        base_filename = payload.base_filename or (
            f"confirmed_quality_rules_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        normalized_format = {
            "json": "custom_json",
            "custom_json": "custom_json",
            "dbt": "dbt_yaml",
            "dbt_yaml": "dbt_yaml",
            "yaml": "dbt_yaml",
        }.get(payload.export_format.lower(), payload.export_format.lower())

        adapter = RuleExportAdapter()
        export_results: list[RuleExportResult] = []
        if normalized_format in {"custom_json", "both"}:
            export_results.append(
                adapter.export_custom_json_rules(
                    confirmed_rules,
                    str(output_dir / f"{base_filename}.json"),
                )
            )
        if normalized_format in {"dbt_yaml", "both"}:
            export_results.append(
                adapter.export_dbt_tests_yaml(
                    confirmed_rules,
                    str(output_dir / f"{base_filename}_dbt.yml"),
                )
            )
        if not export_results:
            raise ValueError(
                "export_format must be one of json, custom_json, dbt, dbt_yaml, yaml, or both."
            )

        return {
            "message": "Confirmed quality rules were exported successfully.",
            "confirmed_rule_count": len(confirmed_rules),
            "rule_export_results": [result.model_dump() for result in export_results],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

"""Review, quality-rule export, and execution-package job routes."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    ConfirmedQualityRuleExportRequest,
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
    MappingReviewSaveRequest,
    QualityRuleReviewRequest,
    StgReviewSaveRequest,
)
from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.review_summary import ReviewSummary
from app.core.models.rule_export_result import RuleExportResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file,
)
from app.core.review.override_store import (
    load_mapping_overrides,
    load_stg_overrides,
    save_mapping_review_records,
    save_stg_review_records,
)
from app.core.review.quality_override_store import (
    load_quality_rule_overrides,
    save_quality_rule_review_records,
)
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.review.review_service import summarize_review_records
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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

        output_dir = Path(payload.output_dir or PROJECT_ROOT / "outputs" / "rule_exports")
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


def _resolve_execution_ready_package_from_payload(
    payload: ExecutionPackageBuildRequest | ExecutionPackageExportRequest,
) -> tuple[ExecutionReadyPackage, list[ConfirmedQualityRule]]:
    """Resolve or build an execution-ready package for API routes."""
    if payload.execution_ready_package is not None:
        return payload.execution_ready_package, list(payload.confirmed_quality_rules)

    confirmed_rules = list(payload.confirmed_quality_rules)
    workflow_result = payload.workflow_result
    if workflow_result is not None and workflow_result.execution_ready_package is not None:
        return workflow_result.execution_ready_package, list(
            workflow_result.confirmed_quality_rules
        )
    if not confirmed_rules and workflow_result is not None:
        confirmed_rules = list(workflow_result.confirmed_quality_rules)

    if not confirmed_rules and payload.file_path:
        workflow_result = (
            run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
                payload.file_path
            )
            if payload.apply_review_replay
            else run_p0_plus_mapping_plus_stg_plus_quality_from_file(payload.file_path)
        )
        if workflow_result.execution_ready_package is not None:
            return workflow_result.execution_ready_package, list(
                workflow_result.confirmed_quality_rules
            )
        confirmed_rules = list(workflow_result.confirmed_quality_rules)

    if (
        not confirmed_rules
        and payload.confirmed_quality_rules == []
        and not payload.file_path
    ):
        raise ValueError(
            "confirmed_quality_rules, workflow_result, execution_ready_package, or file_path is required."
        )

    builder = ExecutionPackageBuilder()
    package = builder.build_package(
        confirmed_rules,
        profile_name=payload.profile_name or "quality_package_only_from_confirmed",
        trace_metadata={"api_route": "execution_ready_package"},
    )
    return package, confirmed_rules


@router.post("/build-execution-ready-package")
def build_execution_ready_package_route(
    payload: ExecutionPackageBuildRequest,
) -> dict[str, object]:
    """Build an execution-ready governance package from confirmed quality rules."""
    try:
        package, confirmed_rules = _resolve_execution_ready_package_from_payload(payload)
        summary = ExecutionPackageBuilder.summarize_package(package)
        return {
            "message": "Execution-ready governance package was built successfully.",
            "confirmed_rule_count": len(confirmed_rules),
            "execution_ready_package": package.model_dump(),
            "execution_package_summary": summary,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/export-execution-ready-package")
def export_execution_ready_package_route(
    payload: ExecutionPackageExportRequest,
) -> dict[str, object]:
    """Export an execution-ready governance package."""
    try:
        package, confirmed_rules = _resolve_execution_ready_package_from_payload(payload)
        output_dir = Path(
            payload.output_dir or PROJECT_ROOT / "outputs" / "execution_packages"
        )
        base_filename = payload.base_filename or (
            f"execution_ready_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        normalized_format = {
            "json": "package_json",
            "package_json": "package_json",
            "manifest": "package_manifest",
            "package_manifest": "package_manifest",
            "dbt": "dbt_yaml",
            "dbt_yaml": "dbt_yaml",
            "yaml": "dbt_yaml",
            "all": "all",
            "both": "all",
        }.get(payload.export_format.lower(), payload.export_format.lower())

        adapter = RuleExportAdapter()
        export_results: list[ExecutionPackageExportResult] = []
        if normalized_format in {"package_json", "all"}:
            export_results.append(
                adapter.export_execution_ready_package_json(
                    package,
                    str(output_dir / f"{base_filename}.json"),
                )
            )
        if normalized_format in {"package_manifest", "all"}:
            export_results.append(
                adapter.export_execution_ready_package_manifest(
                    package,
                    str(output_dir / f"{base_filename}_manifest.json"),
                )
            )
        if normalized_format in {"dbt_yaml", "all"}:
            dbt_result = adapter.export_dbt_tests_yaml(
                package,
                str(output_dir / f"{base_filename}_dbt.yml"),
            )
            export_results.append(
                ExecutionPackageExportResult(
                    export_format=dbt_result.export_format,
                    output_path=dbt_result.output_path,
                    package_id=package.package_id,
                    rule_count=dbt_result.rule_count,
                    status=dbt_result.status,
                    message=dbt_result.message,
                )
            )
        if not export_results:
            raise ValueError(
                "export_format must be one of json, package_json, manifest, package_manifest, dbt, dbt_yaml, yaml, all, or both."
            )

        return {
            "message": "Execution-ready governance package was exported successfully.",
            "package_id": package.package_id,
            "package_rule_count": package.rule_count,
            "confirmed_rule_count": len(confirmed_rules),
            "execution_package_export_results": [
                result.model_dump() for result in export_results
            ],
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/execution-package-summary")
def execution_package_summary_route() -> dict[str, object]:
    """Return a lightweight description of the execution-ready package capability."""
    return {
        "message": "Use POST /jobs/build-execution-ready-package with confirmed rules or file_path to build a package summary.",
        "supported_export_formats": ["package_json", "package_manifest", "dbt_yaml"],
    }


@router.get("/quality-rule-review-summary")
def quality_rule_review_summary_route() -> dict[str, object]:
    """Return quality rule review counts from stored overrides."""
    records = load_quality_rule_overrides()
    return summarize_quality_rule_review_records(records, confirmed_count=0)

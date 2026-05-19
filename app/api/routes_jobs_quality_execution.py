"""Execution-ready package quality job routes."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.job_requests import (
    ExecutionPackageBuildRequest,
    ExecutionPackageExportRequest,
)
from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_from_file,
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
)

router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


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

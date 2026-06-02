"""Service helpers for running governance workflows from local files."""

from __future__ import annotations

from collections.abc import Callable

from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.parser.loader import load_metadata_file
from app.core.parser.manual_metadata_input import save_manual_metadata_records
from app.core.parser.parser_exceptions import ParserError

WorkflowRunner = Callable[[WorkflowEngine, list[TableMeta]], WorkflowResult]


def _run_loaded_workflow(
    file_path: str,
    runner: WorkflowRunner,
    *,
    unexpected_error_prefix: str = "Unexpected error while running the pipeline",
) -> WorkflowResult:
    """Load metadata from a local file, then run the supplied workflow."""
    engine = WorkflowEngine()
    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"{unexpected_error_prefix}: {exc}",
        )

    return runner(engine, tables)


def run_p0_pipeline_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the existing P0 pipeline."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_pipeline(tables),
    )


def save_manual_metadata_to_file(
    records: list[dict[str, object]],
    output_dir: str | None = None,
    *,
    base_filename: str | None = None,
) -> str:
    """Persist small hand-entered metadata records as a reusable CSV file."""
    return save_manual_metadata_records(
        records,
        output_dir=output_dir,
        base_filename=base_filename,
    )


def run_p0_plus_mapping_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping(tables),
    )


def run_p0_plus_mapping_plus_stg_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping plus STG workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg(tables),
    )


def run_p0_plus_mapping_plus_stg_plus_quality_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute diagnosis, mapping, STG, and quality recommendation."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_plus_quality(tables),
    )


def run_p0_plus_mapping_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping workflow with overrides."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_with_review(tables),
    )


def run_p0_plus_mapping_plus_stg_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping plus STG workflow with overrides."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_with_review(tables),
    )


def run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and execute diagnosis, mapping, STG, and quality recommendation with overrides."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review(
            tables
        ),
    )


def run_mapping_only_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the mapping-only workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_standard_mapping(tables),
    )


def run_stg_only_from_mapping_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the mapping plus STG workflow without diagnosis."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_stg_only_from_mapping(tables),
    )


def run_quality_only_from_stg_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute mapping, STG, and quality recommendation."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_quality_only_from_stg(tables),
    )


def run_quality_only_from_stg_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute mapping, STG, quality, and review replay."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_quality_only_from_stg_with_review(tables),
    )


def run_p0_plus_mapping_plus_stg_plus_quality_with_package_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and build an execution package from confirmed rules if present."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_plus_quality_with_package(
            tables
        ),
    )


def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and execute quality review replay plus package build."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package(
            tables
        ),
    )


def run_quality_package_only_from_confirmed_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and build a package using the lightweight quality review chain."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_quality_package_only_from_confirmed(tables),
    )


def run_governance_readiness_assessment_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run readiness assessment without quality review replay."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_governance_readiness_assessment(
            tables,
            apply_review=False,
        ),
    )


def run_governance_readiness_assessment_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run readiness assessment with review replay."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_governance_readiness_assessment(
            tables,
            apply_review=True,
        ),
    )


def run_full_governance_work_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full readiness/remediation work-package workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness(
            tables
        ),
    )


def run_governance_backlog_build_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run backlog build without review replay."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_governance_backlog_build(
            tables,
            apply_review=False,
        ),
    )


def run_governance_backlog_build_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run backlog build with review replay."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_governance_backlog_build(
            tables,
            apply_review=True,
        ),
    )


def run_full_governance_backlog_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full backlog package workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_full_governance_work_package_with_backlog(
            tables
        ),
    )


def run_governance_portfolio_assessment_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run backlog SLA plus portfolio assessment."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_governance_portfolio_assessment(
            tables,
            apply_review=False,
        ),
    )


def run_full_governance_portfolio_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full governance portfolio package workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_full_governance_backlog_with_portfolio(
            tables
        ),
    )


def run_full_governance_delivery_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full governance delivery package workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_full_governance_delivery_package(
            tables,
            apply_review=False,
        ),
    )


def run_full_governance_delivery_package_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run the reviewed governance delivery package workflow."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_full_governance_delivery_package(
            tables,
            apply_review=True,
        ),
    )


def run_confirmation_workbook_only_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and export confirmation workbooks."""
    return _run_loaded_workflow(
        file_path,
        lambda engine, tables: engine.run_confirmation_workbook_only(tables),
    )


def run_batch_governance_workflow_from_files(
    file_paths: list[str],
    group_by: str = "system_name",
    changed_only: bool = False,
    batch_name: str | None = None,
) -> WorkflowResult:
    """Run multi-file batch governance workflow."""
    engine = WorkflowEngine()
    try:
        return engine.run_batch_governance_workflow(
            file_paths=file_paths,
            group_by=group_by,
            changed_only=changed_only,
            batch_name=batch_name,
        )
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running batch governance: {exc}",
        )


def run_batch_governance_delivery_from_files(
    file_paths: list[str],
    group_by: str = "system_name",
    changed_only: bool = False,
    batch_name: str | None = None,
) -> WorkflowResult:
    """Run multi-file batch governance and build a delivery package."""
    engine = WorkflowEngine()
    try:
        return engine.run_batch_governance_delivery(
            file_paths=file_paths,
            group_by=group_by,
            changed_only=changed_only,
            batch_name=batch_name,
        )
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running batch delivery: {exc}",
        )

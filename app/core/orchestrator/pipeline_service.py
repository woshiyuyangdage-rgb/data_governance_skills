"""Service helpers for running the P0 pipeline from local files."""

from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.workflow_engine import WorkflowEngine
from app.core.parser.loader import load_metadata_file
from app.core.parser.parser_exceptions import ParserError


def run_p0_pipeline_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the existing P0 pipeline."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_pipeline(tables)


def run_p0_plus_mapping_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping(tables)


def run_p0_plus_mapping_plus_stg_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping plus STG workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg(tables)


def run_p0_plus_mapping_plus_stg_plus_quality_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute diagnosis, mapping, STG, and quality recommendation."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_plus_quality(tables)


def run_p0_plus_mapping_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping workflow with overrides."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_with_review(tables)


def run_p0_plus_mapping_plus_stg_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the P0 plus mapping plus STG workflow with overrides."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_with_review(tables)


def run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and execute diagnosis, mapping, STG, and quality recommendation with overrides."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review(tables)


def run_mapping_only_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the mapping-only workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_standard_mapping(tables)


def run_stg_only_from_mapping_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute the mapping plus STG workflow without diagnosis."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_stg_only_from_mapping(tables)


def run_quality_only_from_stg_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute mapping, STG, and quality recommendation."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_quality_only_from_stg(tables)


def run_quality_only_from_stg_with_review_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and execute mapping, STG, quality, and review replay."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            confirmed_quality_rules=[],
            quality_rule_review_summary={},
            skill_outputs={},
            status="parser_error",
            message=str(exc),
        )
    except Exception as exc:
        return WorkflowResult(
            input_table_count=0,
            issue_count=0,
            task_count=0,
            issues=[],
            tasks=[],
            mapping_results=[],
            confirmed_mapping_results=[],
            unmapped_fields=[],
            stg_suggestions=[],
            stg_field_suggestions=[],
            confirmed_stg_suggestions=[],
            quality_rule_suggestions=[],
            quality_rule_packages=[],
            confirmed_quality_rules=[],
            quality_rule_review_summary={},
            skill_outputs={},
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_quality_only_from_stg_with_review(tables)


def run_p0_plus_mapping_plus_stg_plus_quality_with_package_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and build an execution package from confirmed rules if present."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_plus_quality_with_package(tables)


def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata from file and execute quality review replay plus package build."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package(tables)


def run_quality_package_only_from_confirmed_from_file(file_path: str) -> WorkflowResult:
    """Load metadata from file and build a package using the lightweight quality review chain."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_quality_package_only_from_confirmed(tables)


def run_governance_readiness_assessment_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run readiness assessment without quality review replay."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_governance_readiness_assessment(tables, apply_review=False)


def run_governance_readiness_assessment_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run readiness assessment with review replay."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_governance_readiness_assessment(tables, apply_review=True)


def run_full_governance_work_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full readiness/remediation work-package workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness(
        tables
    )


def run_governance_backlog_build_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run backlog build without review replay."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_governance_backlog_build(tables, apply_review=False)


def run_governance_backlog_build_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run backlog build with review replay."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_governance_backlog_build(tables, apply_review=True)


def run_full_governance_backlog_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full backlog package workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_full_governance_work_package_with_backlog(tables)


def run_governance_portfolio_assessment_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run backlog SLA plus portfolio assessment."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_governance_portfolio_assessment(tables, apply_review=False)


def run_full_governance_portfolio_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full governance portfolio package workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_full_governance_backlog_with_portfolio(tables)


def run_full_governance_delivery_package_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and run the full governance delivery package workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_full_governance_delivery_package(tables, apply_review=False)


def run_full_governance_delivery_package_with_review_from_file(
    file_path: str,
) -> WorkflowResult:
    """Load metadata and run the reviewed governance delivery package workflow."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_full_governance_delivery_package(tables, apply_review=True)


def run_confirmation_workbook_only_from_file(file_path: str) -> WorkflowResult:
    """Load metadata and export confirmation workbooks."""
    engine = WorkflowEngine()

    try:
        tables = load_metadata_file(file_path)
    except ParserError as exc:
        return WorkflowResult(status="parser_error", message=str(exc))
    except Exception as exc:
        return WorkflowResult(
            status="failed",
            message=f"Unexpected error while running the pipeline: {exc}",
        )

    return engine.run_confirmation_workbook_only(tables)


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

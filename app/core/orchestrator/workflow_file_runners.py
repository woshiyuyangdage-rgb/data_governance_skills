"""File-loading workflow runner helpers."""

from collections.abc import Callable

from app.core.models.table_meta import TableMeta
from app.core.models.workflow_result import WorkflowResult
from app.core.parser.loader import load_metadata_file
from app.core.parser.parser_exceptions import ParserError


class WorkflowFileRunnerMixin:
    """Run table-based workflows from local metadata files."""

    def _run_table_workflow_from_file(
        self,
        file_path: str,
        runner: Callable[[list[TableMeta]], WorkflowResult],
    ) -> WorkflowResult:
        try:
            tables = load_metadata_file(file_path)
        except ParserError as exc:
            return WorkflowResult(status="parser_error", message=str(exc))
        except Exception as exc:
            return WorkflowResult(
                status="failed",
                message=f"Unexpected error while running the pipeline: {exc}",
            )
        return runner(tables)

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata from file and run the confirmed quality rule workflow."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_p0_plus_mapping_plus_stg_plus_quality_with_review,
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata from file and run confirmed quality rules plus package build."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package,
        )

    def run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata and run the full readiness/remediation workflow."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_and_readiness,
        )

    def run_full_governance_work_package_with_backlog_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata and run the full backlog workflow."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_full_governance_work_package_with_backlog,
        )

    def run_full_governance_backlog_with_portfolio_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata and run the full governance portfolio workflow."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_full_governance_backlog_with_portfolio,
        )

    def run_full_governance_delivery_package_from_file(
        self,
        file_path: str,
        apply_review: bool = True,
    ) -> WorkflowResult:
        """Load metadata and run the full delivery package workflow."""
        return self._run_table_workflow_from_file(
            file_path,
            lambda tables: self.run_full_governance_delivery_package(
                tables,
                apply_review=apply_review,
            ),
        )

    def run_confirmation_workbook_only_from_file(
        self,
        file_path: str,
    ) -> WorkflowResult:
        """Load metadata and export confirmation workbooks without package manifest."""
        return self._run_table_workflow_from_file(
            file_path,
            self.run_confirmation_workbook_only,
        )

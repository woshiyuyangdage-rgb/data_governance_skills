"""Shared delivery service for workflow, API, tools, and UI."""

from pathlib import Path
from typing import Any

from app.core.delivery.confirmation_workbook_exporter import ConfirmationWorkbookExporter
from app.core.delivery.governance_delivery_builder import GovernanceDeliveryBuilder
from app.core.models.confirmation_workbook_result import ConfirmationWorkbookResult
from app.core.models.workflow_result import WorkflowResult
from app.core.utils.file_utils import ensure_directory

DEFAULT_DELIVERY_OUTPUT_DIR = (
    Path(__file__).resolve().parents[3] / "app" / "data" / "delivery_packages"
)


class DeliveryService:
    """Lightweight facade over confirmation workbook export and package build."""

    def __init__(self) -> None:
        self.exporter = ConfirmationWorkbookExporter()
        self.builder = GovernanceDeliveryBuilder(self.exporter)

    @staticmethod
    def _base_name(base_name: str | None = None) -> str:
        return (base_name or "governance_delivery_package").strip()

    @staticmethod
    def _ensure_output_dir(output_dir: str | None = None) -> Path:
        path = Path(output_dir) if output_dir else DEFAULT_DELIVERY_OUTPUT_DIR
        ensure_directory(path)
        return path

    @staticmethod
    def _quality_rules_for_confirmation(result: WorkflowResult) -> list[Any]:
        if result.confirmed_quality_rules:
            return list(result.confirmed_quality_rules)
        return list(result.quality_rule_suggestions) + list(result.cross_field_quality_rules)

    def build_confirmation_workbooks(
        self,
        workflow_result: WorkflowResult,
        output_dir: str | None = None,
        base_name: str | None = None,
    ) -> list[ConfirmationWorkbookResult]:
        """Export all standard confirmation workbooks for a workflow result."""
        path = self._ensure_output_dir(output_dir) / self._base_name(base_name)
        ensure_directory(path)
        mapping_results = (
            workflow_result.confirmed_mapping_results or workflow_result.mapping_results
        )
        stg_suggestions = (
            workflow_result.confirmed_stg_suggestions
            or workflow_result.stg_field_suggestions
        )
        results = [
            self.exporter.export_mapping_confirmation_workbook(
                mapping_results,
                str(path / "mapping_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_stg_confirmation_workbook(
                stg_suggestions,
                str(path / "stg_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_quality_rule_confirmation_workbook(
                self._quality_rules_for_confirmation(workflow_result),
                str(path / "quality_rule_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_backlog_delivery_workbook(
                workflow_result.governance_backlog_items,
                str(path / "backlog_workbook.xlsx"),
            ),
        ]
        workflow_result.confirmation_workbook_results = results
        return results

    def build_governance_delivery_package(
        self,
        workflow_result: WorkflowResult,
        output_dir: str | None = None,
        base_name: str | None = None,
        reports: dict[str, str] | None = None,
    ) -> WorkflowResult:
        """Build a directory-based governance delivery package and attach results."""
        output_path = self._ensure_output_dir(output_dir)
        package_name = self._base_name(base_name)
        manifest, package_result, workbook_results = self.builder.build_delivery_package(
            output_dir=str(output_path),
            package_name=package_name,
            mapping_results=workflow_result.mapping_results,
            confirmed_mapping_results=workflow_result.confirmed_mapping_results,
            stg_suggestions=workflow_result.stg_field_suggestions,
            confirmed_stg_suggestions=workflow_result.confirmed_stg_suggestions,
            quality_rule_suggestions=self._quality_rules_for_confirmation(workflow_result),
            confirmed_quality_rules=workflow_result.confirmed_quality_rules,
            governance_backlog_items=workflow_result.governance_backlog_items,
            execution_ready_package=workflow_result.execution_ready_package,
            reports=reports,
        )
        workflow_result.confirmation_workbook_results = workbook_results
        workflow_result.governance_delivery_manifest = manifest
        workflow_result.governance_delivery_package_result = package_result
        skill_outputs = dict(workflow_result.skill_outputs)
        skill_outputs["governance_delivery_output"] = {
            "confirmation_workbook_results": [
                result.model_dump() for result in workbook_results
            ],
            "governance_delivery_manifest": manifest.model_dump(),
            "governance_delivery_package_result": package_result.model_dump(),
        }
        workflow_result.skill_outputs = skill_outputs
        if workflow_result.status == "success":
            workflow_result.message = (
                f"{workflow_result.message} Governance delivery package was also generated."
            )
        return workflow_result


"""Build local governance delivery package directories and manifests."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from app.core.delivery.confirmation_workbook_exporter import ConfirmationWorkbookExporter
from app.core.models.confirmation_workbook_result import ConfirmationWorkbookResult
from app.core.models.governance_delivery_manifest import GovernanceDeliveryManifest
from app.core.models.governance_delivery_package_result import (
    GovernanceDeliveryPackageResult,
)
from app.core.utils.file_utils import ensure_directory


class GovernanceDeliveryBuilder:
    """Build manifest-first local governance delivery packages."""

    def __init__(self, exporter: ConfirmationWorkbookExporter | None = None) -> None:
        self.exporter = exporter or ConfirmationWorkbookExporter()

    @staticmethod
    def _utc_now() -> str:
        return datetime.utcnow().isoformat(timespec="seconds")

    @staticmethod
    def _serialize(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        if isinstance(value, list):
            return [GovernanceDeliveryBuilder._serialize(item) for item in value]
        if isinstance(value, dict):
            return {
                str(key): GovernanceDeliveryBuilder._serialize(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _artifact(
        artifact_type: str,
        path: str,
        row_count: int | None = None,
        status: str = "success",
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "artifact_type": artifact_type,
            "path": path,
            "status": status,
        }
        if row_count is not None:
            payload["row_count"] = row_count
        return payload

    def build_delivery_manifest(
        self,
        package_name: str,
        generated_files: dict[str, str] | None = None,
        workbook_results: list[ConfirmationWorkbookResult] | None = None,
        reports: dict[str, str] | None = None,
        execution_ready_package: Any | None = None,
        summary: str | None = None,
    ) -> GovernanceDeliveryManifest:
        """Build a manifest describing generated delivery artifacts."""
        included_artifacts: list[dict[str, Any]] = []
        generated_files = generated_files or {}
        workbook_results = workbook_results or []
        for result in workbook_results:
            included_artifacts.append(
                self._artifact(
                    result.workbook_type,
                    result.output_path,
                    row_count=result.row_count,
                    status=result.status,
                )
            )
        for artifact_type, path in generated_files.items():
            if artifact_type == "package_manifest":
                continue
            if any(item.get("path") == path for item in included_artifacts):
                continue
            included_artifacts.append(self._artifact(artifact_type, path))
        for report_type, path in (reports or {}).items():
            included_artifacts.append(self._artifact(f"report_{report_type}", path))
        if execution_ready_package is not None:
            package_payload = self._serialize(execution_ready_package)
            included_artifacts.append(
                {
                    "artifact_type": "execution_ready_package",
                    "path": "embedded",
                    "status": "available",
                    "rule_count": package_payload.get("rule_count")
                    if isinstance(package_payload, dict)
                    else None,
                }
            )
        return GovernanceDeliveryManifest(
            package_name=package_name,
            generated_at=self._utc_now(),
            included_artifacts=included_artifacts,
            summary=summary
            or f"Governance delivery package '{package_name}' contains {len(included_artifacts)} artifacts.",
        )

    def _write_manifest(
        self,
        manifest: GovernanceDeliveryManifest,
        manifest_path: Path,
    ) -> str:
        ensure_directory(manifest_path.parent)
        manifest_path.write_text(
            json.dumps(self._serialize(manifest), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(manifest_path)

    def build_delivery_package(
        self,
        output_dir: str,
        package_name: str,
        mapping_results: list[Any] | None = None,
        confirmed_mapping_results: list[Any] | None = None,
        stg_suggestions: list[Any] | None = None,
        confirmed_stg_suggestions: list[Any] | None = None,
        quality_rule_suggestions: list[Any] | None = None,
        confirmed_quality_rules: list[Any] | None = None,
        governance_backlog_items: list[Any] | None = None,
        execution_ready_package: Any | None = None,
        reports: dict[str, str] | None = None,
    ) -> tuple[GovernanceDeliveryManifest, GovernanceDeliveryPackageResult, list[ConfirmationWorkbookResult]]:
        """Build a local directory with confirmation workbooks and manifest."""
        package_dir = Path(output_dir) / package_name
        ensure_directory(package_dir)

        effective_mapping = confirmed_mapping_results or mapping_results or []
        effective_stg = confirmed_stg_suggestions or stg_suggestions or []
        effective_quality = confirmed_quality_rules or quality_rule_suggestions or []
        effective_backlog = governance_backlog_items or []

        workbook_results = [
            self.exporter.export_mapping_confirmation_workbook(
                effective_mapping,
                str(package_dir / "mapping_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_stg_confirmation_workbook(
                effective_stg,
                str(package_dir / "stg_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_quality_rule_confirmation_workbook(
                effective_quality,
                str(package_dir / "quality_rule_confirmation_workbook.xlsx"),
            ),
            self.exporter.export_backlog_delivery_workbook(
                effective_backlog,
                str(package_dir / "backlog_workbook.xlsx"),
            ),
        ]

        generated_files = {
            "mapping_confirmation_workbook": workbook_results[0].output_path,
            "stg_confirmation_workbook": workbook_results[1].output_path,
            "quality_rule_confirmation_workbook": workbook_results[2].output_path,
            "backlog_workbook": workbook_results[3].output_path,
            "package_manifest": str(package_dir / "governance_delivery_manifest.json"),
        }
        manifest = self.build_delivery_manifest(
            package_name=package_name,
            generated_files=generated_files,
            workbook_results=workbook_results,
            reports=reports,
            execution_ready_package=execution_ready_package,
        )
        generated_files["package_manifest"] = self._write_manifest(
            manifest,
            package_dir / "governance_delivery_manifest.json",
        )

        result = GovernanceDeliveryPackageResult(
            package_name=package_name,
            output_dir=str(package_dir),
            generated_files=generated_files,
            status="success",
            message=(
                f"Governance delivery package '{package_name}' generated with "
                f"{len(generated_files)} files."
            ),
        )
        return manifest, result, workbook_results


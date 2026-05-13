"""Tests for delivery service facade."""

from pathlib import Path

from app.core.delivery.delivery_service import DeliveryService
from app.core.models.mapping_result import MappingResult
from app.core.models.workflow_result import WorkflowResult


def test_delivery_service_builds_workbooks_and_package(tmp_path: Path) -> None:
    result = WorkflowResult(
        status="success",
        message="delivery service test",
        mapping_results=[
            MappingResult(
                table_name="customer",
                field_name="customer_id",
                recommended_standard_code="customer_id",
                match_score=1.0,
                match_reason="exact match",
            )
        ],
    )
    service = DeliveryService()

    workbook_results = service.build_confirmation_workbooks(
        result,
        output_dir=str(tmp_path),
        base_name="workbooks",
    )
    assert len(workbook_results) == 4
    assert all(Path(item.output_path).exists() for item in workbook_results)

    packaged_result = service.build_governance_delivery_package(
        result,
        output_dir=str(tmp_path),
        base_name="package",
    )
    assert packaged_result.governance_delivery_manifest is not None
    assert packaged_result.governance_delivery_package_result is not None
    assert Path(
        packaged_result.governance_delivery_package_result.generated_files[
            "package_manifest"
        ]
    ).exists()


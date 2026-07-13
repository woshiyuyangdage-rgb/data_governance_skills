"""Tests for governance delivery package building."""

from pathlib import Path

import pytest

from app.core.delivery.governance_delivery_builder import GovernanceDeliveryBuilder
from app.core.models.mapping_result import MappingResult
from app.core.utils import file_utils
from app.core.utils.file_utils import LocalPathAccessError


def test_governance_delivery_builder_builds_manifest_and_package(
    tmp_path: Path,
) -> None:
    builder = GovernanceDeliveryBuilder()

    manifest, package_result, workbook_results = builder.build_delivery_package(
        output_dir=str(tmp_path),
        package_name="delivery_test",
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

    assert manifest.package_name == "delivery_test"
    assert manifest.included_artifacts
    assert package_result.status == "success"
    assert Path(package_result.output_dir).exists()
    assert set(package_result.generated_files) >= {
        "mapping_confirmation_workbook",
        "stg_confirmation_workbook",
        "quality_rule_confirmation_workbook",
        "backlog_workbook",
        "package_manifest",
    }
    assert len(workbook_results) == 4
    assert Path(package_result.generated_files["package_manifest"]).exists()


def test_governance_delivery_builder_rejects_output_dir_outside_allowed_roots(
    monkeypatch,
    tmp_path: Path,
) -> None:
    safe_root = tmp_path / "safe_project"
    outside_dir = tmp_path / "outside"
    safe_root.mkdir()
    monkeypatch.setattr(file_utils, "PROJECT_ROOT", safe_root)
    monkeypatch.delenv(file_utils.ALLOWED_LOCAL_ROOTS_ENV, raising=False)

    with pytest.raises(LocalPathAccessError):
        GovernanceDeliveryBuilder().build_delivery_package(
            output_dir=str(outside_dir),
            package_name="outside_delivery",
        )

    assert not outside_dir.exists()

"""Smoke tests for metadata intake adapter service."""

import pandas as pd

from app.core.intake.intake_adapter_service import IntakeAdapterService


def test_intake_adapter_normalizes_governance_platform_export(tmp_path) -> None:
    file_path = tmp_path / "platform.csv"
    pd.DataFrame(
        [
            {
                "物理表名": "cust_table",
                "物理字段名": "cust_id",
                "字段类型": "varchar",
                "可空": "否",
                "额外列": "ignored",
            }
        ]
    ).to_csv(file_path, index=False)

    result = IntakeAdapterService().normalize_metadata_input(
        str(file_path),
        profile_name="governance_platform_export_template",
    )

    assert result.status == "success"
    assert result.row_count == 1
    assert result.table_count == 1
    assert result.normalized_records[0]["table_name"] == "cust_table"
    assert result.normalized_records[0]["nullable"] is False
    assert result.mapping_result is not None
    assert "额外列" in result.mapping_result.unmapped_source_columns


def test_intake_adapter_reports_missing_required_fields(tmp_path) -> None:
    file_path = tmp_path / "missing.csv"
    pd.DataFrame([{"物理表名": "cust_table", "字段类型": "varchar"}]).to_csv(
        file_path,
        index=False,
    )

    result = IntakeAdapterService().normalize_metadata_input(
        str(file_path),
        profile_name="governance_platform_export_template",
    )

    assert result.status == "failed"
    assert result.mapping_result is not None
    assert "field_name" in result.mapping_result.missing_required_fields


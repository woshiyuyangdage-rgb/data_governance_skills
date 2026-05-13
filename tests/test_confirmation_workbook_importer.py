"""Tests for confirmation workbook import."""

from pathlib import Path

import pandas as pd

from app.core.delivery.confirmation_workbook_importer import ConfirmationWorkbookImporter


def _write_workbook(path: Path, sheet_name: str, rows: list[dict[str, object]]) -> str:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)
    return str(path)


def test_importer_validates_and_imports_mapping_aliases(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "mapping.xlsx",
        "mapping",
        [
            {
                "table_name": "customer",
                "field_name": "customer_id",
                "standard_code": "customer_id",
                "status": "accepted",
                "comments": "ok",
            }
        ],
    )
    importer = ConfirmationWorkbookImporter()

    validation = importer.validate_workbook(path, "mapping_confirmation")
    payload = importer.import_mapping_confirmation_workbook(path)

    assert validation.is_valid is True
    assert payload.import_summary.imported_count == 1
    assert payload.normalized_rows[0]["confirmation_status"] == "accept"
    assert payload.normalized_rows[0]["reviewer_note"] == "ok"


def test_importer_imports_stg_quality_and_backlog_workbooks(tmp_path: Path) -> None:
    importer = ConfirmationWorkbookImporter()
    stg_path = _write_workbook(
        tmp_path / "stg.xlsx",
        "stg_confirmation",
        [
            {
                "source_table_name": "customer",
                "source_field_name": "cust_id",
                "recommended_stg_field_name": "customer_id",
                "confirmation_status": "edit",
            }
        ],
    )
    quality_path = _write_workbook(
        tmp_path / "quality.xlsx",
        "quality_rules",
        [
            {
                "source_table_name": "customer",
                "source_field_name": "customer_id",
                "rule_type": "not_null",
                "confirmation_status": "manual_review",
            }
        ],
    )
    backlog_path = _write_workbook(
        tmp_path / "backlog.xlsx",
        "backlog",
        [
            {
                "backlog_id": "backlog_1",
                "confirmation_status": "accepted",
            }
        ],
    )

    assert importer.import_stg_confirmation_workbook(stg_path).import_summary.edited_count == 1
    assert (
        importer.import_quality_rule_confirmation_workbook(
            quality_path
        ).import_summary.manual_review_count
        == 1
    )
    assert importer.import_backlog_confirmation_workbook(backlog_path).import_summary.imported_count == 1


def test_importer_template_aware_import_maps_business_columns(tmp_path: Path) -> None:
    path = _write_workbook(
        tmp_path / "business_mapping.xlsx",
        "mapping_review",
        [
            {
                "表名": "customer",
                "字段名": "customer_id",
                "标准编码": "customer_id",
                "确认结果": "accepted",
                "业务备注": "business ok",
            }
        ],
    )
    importer = ConfirmationWorkbookImporter()

    payload = importer.import_confirmation_with_template(
        path,
        workbook_type="mapping_confirmation",
    )

    assert payload.import_summary.imported_count == 1
    assert payload.confirmation_template_match_result is not None
    assert (
        payload.confirmation_template_match_result.matched_template_name
        == "business_mapping_review_template"
    )
    assert payload.confirmation_template_mapping_result is not None
    assert payload.confirmation_template_mapping_result.status == "success"
    assert payload.normalized_rows[0]["source_table_name"] == "customer"
    assert payload.normalized_rows[0]["reviewer_note"] == "business ok"


def test_importer_uses_selected_template_to_choose_best_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "multi_sheet_mapping.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame([{"noise": "x"}]).to_excel(writer, sheet_name="cover", index=False)
        pd.DataFrame(
            [
                {
                    "表名": "customer",
                    "字段名": "customer_id",
                    "确认结果": "accepted",
                }
            ]
        ).to_excel(writer, sheet_name="业务确认", index=False)

    payload = ConfirmationWorkbookImporter().import_confirmation_with_template(
        str(workbook_path),
        template_name="business_mapping_review_template",
    )

    assert payload.import_summary.imported_count == 1
    assert payload.confirmation_template_match_result is not None
    assert payload.confirmation_template_match_result.matched_sheet_name == "业务确认"


def test_importer_imports_standard_csv_confirmation_with_template(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "mapping.csv"
    pd.DataFrame(
        [
            {
                "source_table_name": "customer",
                "source_field_name": "customer_id",
                "confirmation_status": "accepted",
            }
        ]
    ).to_csv(csv_path, index=False)

    payload = ConfirmationWorkbookImporter().import_confirmation_with_template(
        str(csv_path),
        template_name="standard_mapping_confirmation_template",
    )

    assert payload.import_summary.imported_count == 1
    assert payload.normalized_rows[0]["confirmation_status"] == "accept"


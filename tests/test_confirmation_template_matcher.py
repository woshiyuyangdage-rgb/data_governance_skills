"""Tests for confirmation workbook template matching."""

from pathlib import Path

import pandas as pd

from app.core.delivery.confirmation_template_matcher import ConfirmationTemplateMatcher


def _write_workbook(path: Path, sheet_name: str, rows: list[dict[str, object]]) -> str:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name=sheet_name, index=False)
    return str(path)


def test_confirmation_template_matcher_matches_business_mapping_template(
    tmp_path: Path,
) -> None:
    file_path = _write_workbook(
        tmp_path / "business_mapping.xlsx",
        "mapping_review",
        [
            {
                "表名": "customer",
                "字段名": "customer_id",
                "标准编码": "customer_id",
                "确认结果": "accepted",
                "业务备注": "ok",
            }
        ],
    )

    result = ConfirmationTemplateMatcher().match(
        file_path,
        workbook_type="mapping_confirmation",
    )

    assert result.matched_template_name == "business_mapping_review_template"
    assert result.workbook_type == "mapping_confirmation"
    assert result.matched_sheet_name == "mapping_review"
    assert result.fallback_used is False
    assert result.confidence and result.confidence >= 0.8


def test_confirmation_template_matcher_reports_fallback_for_unknown_headers(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "unknown.csv"
    pd.DataFrame([{"unknown_a": "x", "unknown_b": "y"}]).to_csv(file_path, index=False)

    result = ConfirmationTemplateMatcher().match(str(file_path))

    assert result.matched_template_name is None
    assert result.fallback_used is True
    assert result.confidence == 0.0

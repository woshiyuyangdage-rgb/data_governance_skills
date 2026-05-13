"""Smoke tests for metadata intake template matching."""

import pandas as pd

from app.core.intake.intake_template_matcher import IntakeTemplateMatcher


def _write_csv(path, columns: list[str]) -> str:
    pd.DataFrame([{column: "x" for column in columns}]).to_csv(path, index=False)
    return str(path)


def test_intake_matcher_matches_standard_template(tmp_path) -> None:
    file_path = _write_csv(tmp_path / "standard.csv", ["table_name", "field_name", "data_type"])
    result = IntakeTemplateMatcher().match(file_path)
    assert result.matched_profile_name == "standard_metadata_template"
    assert result.fallback_used is False


def test_intake_matcher_matches_governance_platform_template(tmp_path) -> None:
    file_path = _write_csv(tmp_path / "platform.csv", ["物理表名", "物理字段名", "字段类型"])
    result = IntakeTemplateMatcher().match(file_path)
    assert result.matched_profile_name == "governance_platform_export_template"


def test_intake_matcher_matches_manual_inventory_template(tmp_path) -> None:
    file_path = _write_csv(tmp_path / "inventory.csv", ["table", "字段名", "表中文名"])
    result = IntakeTemplateMatcher().match(file_path)
    assert result.matched_profile_name == "manual_inventory_template"


def test_intake_matcher_fallback_for_unrelated_headers(tmp_path) -> None:
    file_path = _write_csv(tmp_path / "unknown.csv", ["foo", "bar"])
    result = IntakeTemplateMatcher().match(file_path)
    assert result.fallback_used is True
    assert result.matched_profile_name is None


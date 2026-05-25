"""Tests for confirmed quality rule export adapters."""

import json
from pathlib import Path

import yaml

from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule

OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / ".pytest_runtime"
    / "test_rule_export_adapter"
)


def _output_path(filename: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / filename


def _rules() -> list[ConfirmedQualityRule]:
    return [
        ConfirmedQualityRule(
            source_table_name="sales_order",
            source_field_name="order_id",
            recommended_field_name="order_id",
            rule_type="not_null",
            rule_expression="not_null",
            severity="high",
            priority="P1",
            confirmation_source="override_accept",
            reason="identifier",
        ),
        ConfirmedQualityRule(
            source_table_name="sales_order",
            source_field_name="status",
            recommended_field_name="status",
            rule_type="value_set",
            rule_expression="value in ('OPEN','CLOSED')",
            severity="medium",
            priority="P2",
            confirmation_source="override_edit",
            reason="status code",
        ),
    ]


def _cross_field_rules() -> list[ConfirmedQualityRule]:
    return _rules() + [
        ConfirmedQualityRule(
            source_table_name="sales_order",
            source_field_name="start_date",
            rule_scope="cross_field",
            field_group=["start_date", "end_date"],
            rule_type="temporal_order",
            rule_expression="start_date <= end_date",
            severity="medium",
            priority="P2",
            confidence=1.0,
            review_priority="medium_review_priority",
            confirmation_source="override_accept",
            reason="date order",
        )
    ]


def _cross_table_rules() -> list[ConfirmedQualityRule]:
    return _rules() + [
        ConfirmedQualityRule(
            source_table_name="contract_info",
            source_field_name="customer_id",
            rule_name="contract_info.customer_id references customer_master.customer_id",
            rule_scope="cross_table",
            field_group=["customer_id"],
            target_table_name="customer_master",
            target_field_name="customer_id",
            rule_type="cross_table_reference",
            rule_expression="contract_info.customer_id exists in customer_master.customer_id",
            severity="medium",
            priority="P2",
            risk_level="medium",
            confidence=0.8,
            review_priority="medium_review_priority",
            confirmation_source="override_accept",
            reason="Foreign key should resolve to parent table.",
            export_formats=["excel_quality_rule_list", "json_rule_package", "custom_sql_check"],
        )
    ]


def test_export_custom_json_rules_succeeds() -> None:
    adapter = RuleExportAdapter()
    output_path = _output_path("rules.json")

    result = adapter.export_custom_json_rules(_rules(), str(output_path))
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert result.rule_count == 2
    assert payload["rule_count"] == 2
    assert payload["rules"][0]["table"] == "sales_order"
    assert payload["rules"][0]["field"] == "order_id"


def test_export_dbt_tests_yaml_succeeds() -> None:
    adapter = RuleExportAdapter()
    output_path = _output_path("rules.yml")

    result = adapter.export_dbt_tests_yaml(_rules(), str(output_path))
    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert result.rule_count == 2
    assert payload["version"] == 2
    assert payload["models"][0]["name"] == "sales_order"
    order_id_column = next(
        column for column in payload["models"][0]["columns"] if column["name"] == "order_id"
    )
    assert "not_null" in order_id_column["tests"]


def test_export_execution_package_json_and_manifest_succeed() -> None:
    adapter = RuleExportAdapter()
    package = ExecutionPackageBuilder().build_package(
        _rules(),
        profile_name="test_package_profile",
    )
    json_path = _output_path("package.json")
    manifest_path = _output_path("manifest.json")

    json_result = adapter.export_execution_ready_package_json(package, str(json_path))
    manifest_result = adapter.export_execution_ready_package_manifest(
        package,
        str(manifest_path),
    )
    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert json_result.status == "success"
    assert manifest_result.status == "success"
    assert json_result.rule_count == 2
    assert manifest_result.rule_count == 2
    assert json_payload["package_id"] == package.package_id
    assert manifest_payload["rule_count"] == 2
    assert manifest_payload["rules_summary"][0]["rule_id"].startswith("rule_")


def test_export_dbt_tests_yaml_from_execution_package() -> None:
    adapter = RuleExportAdapter()
    package = ExecutionPackageBuilder().build_package(_rules())
    output_path = _output_path("package_dbt.yml")

    result = adapter.export_dbt_tests_yaml(package, str(output_path))
    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))

    assert result.status == "success"
    assert result.rule_count == package.rule_count
    assert payload["meta"]["package_id"] == package.package_id


def test_cross_field_rules_are_preserved_in_json_and_manifest() -> None:
    adapter = RuleExportAdapter()
    package = ExecutionPackageBuilder().build_package(_cross_field_rules())
    json_path = _output_path("cross_field_rules.json")
    manifest_path = _output_path("cross_field_manifest.json")

    json_result = adapter.export_custom_json_rules(_cross_field_rules(), str(json_path))
    manifest_result = adapter.export_execution_ready_package_manifest(
        package,
        str(manifest_path),
    )
    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert json_result.rule_count == 3
    assert manifest_result.rule_count == 3
    assert json_payload["exported_cross_field_rule_count"] == 1
    assert manifest_payload["exported_cross_field_rule_count"] == 1
    assert manifest_payload["non_native_rule_count"] >= 1


def test_cross_field_rules_export_to_dbt_as_non_native_metadata() -> None:
    adapter = RuleExportAdapter()
    package = ExecutionPackageBuilder().build_package(_cross_field_rules())
    output_path = _output_path("cross_field_dbt.yml")

    result = adapter.export_dbt_tests_yaml(package, str(output_path))
    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    start_column = next(
        column for column in payload["models"][0]["columns"] if column["name"] == "start_date"
    )

    assert result.rule_count == 3
    assert payload["meta"]["exported_cross_field_rule_count"] == 1
    assert payload["meta"]["non_native_rule_count"] >= 1
    assert start_column["tests"][0]["quality_rule_meta"]["non_native_test"] is True


def test_cross_table_rules_are_preserved_in_json_and_dbt_metadata() -> None:
    adapter = RuleExportAdapter()
    package = ExecutionPackageBuilder().build_package(_cross_table_rules())
    json_path = _output_path("cross_table_rules.json")
    dbt_path = _output_path("cross_table_dbt.yml")

    json_result = adapter.export_custom_json_rules(_cross_table_rules(), str(json_path))
    dbt_result = adapter.export_dbt_tests_yaml(package, str(dbt_path))
    json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    dbt_payload = yaml.safe_load(dbt_path.read_text(encoding="utf-8"))
    contract_model = next(
        model for model in dbt_payload["models"] if model["name"] == "contract_info"
    )
    customer_column = next(
        column for column in contract_model["columns"] if column["name"] == "customer_id"
    )
    meta = customer_column["tests"][0]["quality_rule_meta"]

    assert json_result.rule_count == 3
    assert dbt_result.rule_count == 3
    assert json_payload["exported_cross_field_rule_count"] == 1
    assert json_payload["rules"][-1]["target_table"] == "customer_master"
    assert meta["rule_scope"] == "cross_table"
    assert meta["target_table_name"] == "customer_master"
    assert meta["non_native_test"] is True

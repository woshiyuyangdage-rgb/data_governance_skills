"""Adapters for exporting confirmed rules and execution-ready rule packages."""

from collections import defaultdict
import json
from pathlib import Path
from typing import Any

import yaml

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.execution_ready_rule import ExecutionReadyRule
from app.core.models.rule_export_result import RuleExportResult
from app.core.utils.file_utils import ensure_directory
from app.core.utils.time_utils import utc_now_seconds


def _utc_now() -> str:
    return utc_now_seconds()


def _coerce_confirmed_rule(
    rule: ConfirmedQualityRule | dict[str, object],
) -> ConfirmedQualityRule:
    if isinstance(rule, ConfirmedQualityRule):
        return rule
    return ConfirmedQualityRule.model_validate(rule)


def _coerce_execution_rule(
    rule: ExecutionReadyRule | dict[str, object],
) -> ExecutionReadyRule:
    if isinstance(rule, ExecutionReadyRule):
        return rule
    return ExecutionReadyRule.model_validate(rule)


def _coerce_package(
    package: ExecutionReadyPackage | dict[str, object],
) -> ExecutionReadyPackage:
    if isinstance(package, ExecutionReadyPackage):
        return package
    return ExecutionReadyPackage.model_validate(package)


class RuleExportAdapter:
    """Export confirmed quality rules and execution-ready packages."""

    @staticmethod
    def group_rules_by_table_and_field(
        confirmed_rules: list[ConfirmedQualityRule | dict[str, object]],
    ) -> dict[str, dict[str, list[ConfirmedQualityRule]]]:
        """Group confirmed rules by source table and field."""
        grouped: dict[str, dict[str, list[ConfirmedQualityRule]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for raw_rule in confirmed_rules:
            rule = _coerce_confirmed_rule(raw_rule)
            grouped[rule.source_table_name][rule.source_field_name].append(rule)
        return grouped

    @staticmethod
    def group_execution_rules_by_table_and_field(
        rules: list[ExecutionReadyRule | dict[str, object]],
    ) -> dict[str, dict[str, list[ExecutionReadyRule]]]:
        """Group execution-ready rules by source table and field."""
        grouped: dict[str, dict[str, list[ExecutionReadyRule]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for raw_rule in rules:
            rule = _coerce_execution_rule(raw_rule)
            grouped[rule.source_table_name][rule.source_field_name].append(rule)
        return grouped

    @staticmethod
    def build_custom_json_package(
        confirmed_rules: list[ConfirmedQualityRule | dict[str, object]],
    ) -> dict[str, object]:
        """Build the backward-compatible custom JSON rule package payload."""
        package = ExecutionPackageBuilder().build_package(confirmed_rules)
        return RuleExportAdapter.build_custom_json_package_from_execution_package(package)

    @staticmethod
    def build_custom_json_package_from_execution_package(
        package: ExecutionReadyPackage | dict[str, object],
    ) -> dict[str, object]:
        """Build the custom JSON rule package payload from the execution contract."""
        resolved_package = _coerce_package(package)
        field_rule_count = sum(
            1 for rule in resolved_package.rules if rule.rule_scope == "field"
        )
        cross_field_rule_count = sum(
            1 for rule in resolved_package.rules if rule.rule_scope in {"cross_field", "cross_table"}
        )
        non_native_rule_count = sum(
            1
            for rule in resolved_package.rules
            if rule.rule_scope != "field" or not rule.engine_hints.get("dbt")
        )
        return {
            "generated_at": _utc_now(),
            "package_id": resolved_package.package_id,
            "rule_count": resolved_package.rule_count,
            "exported_field_rule_count": field_rule_count,
            "exported_cross_field_rule_count": cross_field_rule_count,
            "non_native_rule_count": non_native_rule_count,
            "rules": [
                {
                    "rule_id": rule.rule_id,
                    "table": rule.source_table_name,
                    "field": rule.source_field_name,
                    "rule_name": rule.rule_name,
                    "rule_description": rule.rule_description,
                    "field_group": rule.field_group,
                    "target_table": rule.target_table_name,
                    "target_field": rule.target_field_name,
                    "rule_type": rule.rule_type,
                    "rule_scope": rule.rule_scope,
                    "semantic_type": rule.semantic_type,
                    "rule_expression": rule.rule_expression,
                    "execution_expression": rule.execution_expression,
                    "execution_mode": rule.execution_mode,
                    "severity": rule.severity,
                    "priority": rule.priority,
                    "risk_level": rule.risk_level,
                    "confidence": rule.confidence,
                    "review_priority": rule.review_priority,
                    "confirmation_source": rule.confirmation_source,
                    "match_basis": rule.match_basis,
                    "reason": rule.reason,
                    "export_formats": rule.export_formats,
                    "engine_hints": rule.engine_hints,
                    "notes": rule.notes,
                }
                for rule in resolved_package.rules
            ],
        }

    @staticmethod
    def map_quality_rule_to_dbt_test(rule: ConfirmedQualityRule) -> Any:
        """Map one confirmed rule to a first-version dbt test or metadata placeholder."""
        rule_type = rule.rule_type.strip().lower()
        if rule_type == "not_null":
            return "not_null"
        if rule_type == "uniqueness":
            return "unique"
        if rule_type == "value_set":
            return {
                "accepted_values": {
                    "values": [],
                    "meta": {
                        "rule_expression": rule.rule_expression,
                        "severity": rule.severity,
                        "priority": rule.priority,
                    },
                }
            }
        return {
            "quality_rule_meta": {
                "rule_type": rule.rule_type,
                "rule_expression": rule.rule_expression,
                "severity": rule.severity,
                "priority": rule.priority,
                "reason": rule.reason,
            }
        }

    @staticmethod
    def map_execution_rule_to_dbt_test(rule: ExecutionReadyRule) -> Any:
        """Map one execution-ready rule to a first-version dbt test shape."""
        if rule.rule_scope != "field":
            return {
                "quality_rule_meta": {
                    "rule_id": rule.rule_id,
                    "rule_scope": rule.rule_scope,
                    "rule_name": rule.rule_name,
                    "rule_description": rule.rule_description,
                    "field_group": rule.field_group,
                    "target_table_name": rule.target_table_name,
                    "rule_type": rule.rule_type,
                    "semantic_type": rule.semantic_type,
                    "rule_expression": rule.rule_expression,
                    "execution_expression": rule.execution_expression,
                    "execution_mode": rule.execution_mode,
                    "severity": rule.severity,
                    "priority": rule.priority,
                    "risk_level": rule.risk_level,
                    "confidence": rule.confidence,
                    "review_priority": rule.review_priority,
                    "non_native_test": True,
                    "adapter_note": (
                        "Non-field rule is carried as metadata in the first-version dbt adapter."
                    ),
                }
            }
        dbt_hint = str(rule.engine_hints.get("dbt", "")).strip().lower()
        rule_type = rule.rule_type.strip().lower()
        mapped = dbt_hint or {
            "not_null": "not_null",
            "uniqueness": "unique",
            "value_set": "accepted_values",
        }.get(rule_type, "")

        if mapped == "not_null":
            return "not_null"
        if mapped in {"unique", "uniqueness"}:
            return "unique"
        if mapped == "accepted_values":
            return {
                "accepted_values": {
                    "values": [],
                    "meta": {
                        "rule_id": rule.rule_id,
                        "rule_expression": rule.rule_expression,
                        "execution_expression": rule.execution_expression,
                        "severity": rule.severity,
                        "priority": rule.priority,
                    },
                }
            }
        return {
            "quality_rule_meta": {
                        "rule_id": rule.rule_id,
                        "rule_scope": rule.rule_scope,
                        "rule_type": rule.rule_type,
                "semantic_type": rule.semantic_type,
                "rule_expression": rule.rule_expression,
                "execution_expression": rule.execution_expression,
                "execution_mode": rule.execution_mode,
                "severity": rule.severity,
                "priority": rule.priority,
                "reason": rule.reason,
            }
        }

    @classmethod
    def build_dbt_yaml_structure(
        cls,
        confirmed_rules: (
            list[ConfirmedQualityRule | dict[str, object]]
            | ExecutionReadyPackage
            | dict[str, object]
        ),
    ) -> dict[str, object]:
        """Build a dbt tests YAML structure grouped by table and field."""
        if isinstance(confirmed_rules, (ExecutionReadyPackage, dict)):
            package = _coerce_package(confirmed_rules)
            grouped = cls.group_execution_rules_by_table_and_field(package.rules)
            field_rule_count = sum(1 for rule in package.rules if rule.rule_scope == "field")
            cross_field_rule_count = sum(1 for rule in package.rules if rule.rule_scope in {"cross_field", "cross_table"})
            non_native_rule_count = sum(
                1
                for rule in package.rules
                if rule.rule_scope != "field" or not rule.engine_hints.get("dbt")
            )
            models: list[dict[str, object]] = []
            for table_name in sorted(grouped):
                columns: list[dict[str, object]] = []
                for field_name in sorted(grouped[table_name]):
                    rules = grouped[table_name][field_name]
                    tests = [cls.map_execution_rule_to_dbt_test(rule) for rule in rules]
                    columns.append(
                        {
                            "name": field_name,
                            "tests": tests,
                            "meta": {
                                "execution_ready_rules": [
                                    {
                                        "rule_id": rule.rule_id,
                                        "rule_scope": rule.rule_scope,
                                        "rule_name": rule.rule_name,
                                        "field_group": rule.field_group,
                                        "target_table_name": rule.target_table_name,
                                        "rule_type": rule.rule_type,
                                        "semantic_type": rule.semantic_type,
                                        "execution_mode": rule.execution_mode,
                                        "severity": rule.severity,
                                        "priority": rule.priority,
                                        "risk_level": rule.risk_level,
                                    }
                                    for rule in rules
                                ]
                            },
                        }
                    )
                models.append({"name": table_name, "columns": columns})

            return {
                "version": 2,
                "models": models,
                "meta": {
                    "generated_at": _utc_now(),
                    "package_id": package.package_id,
                    "rule_count": package.rule_count,
                    "exported_field_rule_count": field_rule_count,
                    "exported_cross_field_rule_count": cross_field_rule_count,
                    "non_native_rule_count": non_native_rule_count,
                    "adapter_note": (
                        "First-version dbt tests adapter. Non-native rules are emitted "
                        "as metadata placeholders for later custom test or macro mapping."
                    ),
                },
            }

        package = ExecutionPackageBuilder().build_package(confirmed_rules)
        return cls.build_dbt_yaml_structure(package)

    @staticmethod
    def build_execution_ready_package_manifest(
        package: ExecutionReadyPackage | dict[str, object],
    ) -> dict[str, object]:
        """Build a lightweight JSON manifest for one execution-ready package."""
        resolved_package = _coerce_package(package)
        field_rule_count = sum(
            1 for rule in resolved_package.rules if rule.rule_scope == "field"
        )
        cross_field_rule_count = sum(
            1 for rule in resolved_package.rules if rule.rule_scope in {"cross_field", "cross_table"}
        )
        non_native_rule_count = sum(
            1
            for rule in resolved_package.rules
            if rule.rule_scope != "field" or not rule.engine_hints.get("dbt")
        )
        return {
            "generated_at": _utc_now(),
            "package_id": resolved_package.package_id,
            "package_name": resolved_package.package_name,
            "rule_count": resolved_package.rule_count,
            "exported_field_rule_count": field_rule_count,
            "exported_cross_field_rule_count": cross_field_rule_count,
            "non_native_rule_count": non_native_rule_count,
            "source_profile": resolved_package.source_profile,
            "compatibility": resolved_package.compatibility,
            "rules_summary": [
                {
                    "rule_id": rule.rule_id,
                    "target": f"{rule.source_table_name}.{rule.source_field_name}",
                    "rule_name": rule.rule_name,
                    "field_group": rule.field_group,
                    "target_table_name": rule.target_table_name,
                    "target_field_name": rule.target_field_name,
                    "rule_scope": rule.rule_scope,
                    "rule_type": rule.rule_type,
                    "semantic_type": rule.semantic_type,
                    "execution_mode": rule.execution_mode,
                    "severity": rule.severity,
                    "priority": rule.priority,
                    "risk_level": rule.risk_level,
                    "confidence": rule.confidence,
                    "review_priority": rule.review_priority,
                    "engine_hints": rule.engine_hints,
                }
                for rule in resolved_package.rules
            ],
        }

    def export_custom_json_rules(
        self,
        confirmed_rules: list[ConfirmedQualityRule | dict[str, object]],
        output_path: str,
    ) -> RuleExportResult:
        """Export confirmed rules as a custom JSON package."""
        payload = self.build_custom_json_package(confirmed_rules)
        path = Path(output_path)
        ensure_directory(path.parent)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return RuleExportResult(
            export_format="custom_json",
            output_path=str(path),
            rule_count=int(payload["rule_count"]),
            status="success",
            message="Confirmed quality rules were exported as a custom JSON package.",
        )

    def export_dbt_tests_yaml(
        self,
        confirmed_rules: (
            list[ConfirmedQualityRule | dict[str, object]]
            | ExecutionReadyPackage
            | dict[str, object]
        ),
        output_path: str,
    ) -> RuleExportResult:
        """Export rules as a first-version dbt tests YAML file."""
        payload = self.build_dbt_yaml_structure(confirmed_rules)
        path = Path(output_path)
        ensure_directory(path.parent)
        path.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return RuleExportResult(
            export_format="dbt_yaml",
            output_path=str(path),
            rule_count=int(payload["meta"]["rule_count"]),
            status="success",
            message="Rules were exported as first-version dbt tests YAML.",
        )

    def export_execution_ready_package_json(
        self,
        package: ExecutionReadyPackage | dict[str, object],
        output_path: str,
    ) -> ExecutionPackageExportResult:
        """Export the full execution-ready package contract as JSON."""
        resolved_package = _coerce_package(package)
        path = Path(output_path)
        ensure_directory(path.parent)
        path.write_text(
            json.dumps(resolved_package.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ExecutionPackageExportResult(
            export_format="package_json",
            output_path=str(path),
            package_id=resolved_package.package_id,
            rule_count=resolved_package.rule_count,
            status="success",
            message="Execution-ready package was exported as JSON.",
        )

    def export_execution_ready_package_manifest(
        self,
        package: ExecutionReadyPackage | dict[str, object],
        output_path: str,
    ) -> ExecutionPackageExportResult:
        """Export a lightweight execution-ready package manifest as JSON."""
        resolved_package = _coerce_package(package)
        payload = self.build_execution_ready_package_manifest(resolved_package)
        path = Path(output_path)
        ensure_directory(path.parent)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return ExecutionPackageExportResult(
            export_format="package_manifest",
            output_path=str(path),
            package_id=resolved_package.package_id,
            rule_count=resolved_package.rule_count,
            status="success",
            message="Execution-ready package manifest was exported as JSON.",
        )


# TODO: add Great Expectations and Soda package adapters after the package contract stabilizes.

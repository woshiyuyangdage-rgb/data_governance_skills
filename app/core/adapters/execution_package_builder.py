"""Build execution-ready governance packages from confirmed quality rules."""

from datetime import datetime
import hashlib
from typing import Any

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.execution_ready_rule import ExecutionReadyRule
from app.core.rules.config_loader import (
    get_execution_package_policies_config,
    get_rule_execution_templates_config,
)


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _coerce_confirmed_rule(rule: ConfirmedQualityRule | dict[str, object]) -> ConfirmedQualityRule:
    if isinstance(rule, ConfirmedQualityRule):
        return rule
    return ConfirmedQualityRule.model_validate(rule)


class ExecutionPackageBuilder:
    """Convert confirmed quality rules into a stable execution contract package."""

    def __init__(
        self,
        policies: dict[str, Any] | None = None,
        templates: dict[str, Any] | None = None,
    ) -> None:
        self.policies = policies or get_execution_package_policies_config()
        self.templates = templates or get_rule_execution_templates_config()

    @staticmethod
    def build_rule_id(rule: ConfirmedQualityRule) -> str:
        """Build a deterministic rule identity from the confirmed rule target."""
        identity = "|".join(
            [
                rule.source_table_name.strip().lower(),
                rule.source_field_name.strip().lower(),
                rule.rule_scope.strip().lower(),
                ",".join(sorted(rule.field_group)),
                rule.rule_type.strip().lower(),
                str(rule.rule_expression or "").strip().lower(),
            ]
        )
        return f"rule_{hashlib.sha1(identity.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def build_package_id(
        rules: list[ExecutionReadyRule],
        profile_name: str | None = None,
    ) -> str:
        """Build a deterministic package identity from included rule ids."""
        identity = "|".join(
            [str(profile_name or "package")]
            + sorted(rule.rule_id for rule in rules)
            + [str(len(rules))]
        )
        return f"exec_pkg_{hashlib.sha1(identity.encode('utf-8')).hexdigest()[:16]}"

    def map_rule_type_to_execution_template(self, rule_type: str) -> dict[str, Any]:
        """Return the execution semantic template for one rule type."""
        templates = self.templates.get("templates", {})
        if not isinstance(templates, dict):
            return {}
        template = templates.get(str(rule_type).strip().lower(), {})
        return template if isinstance(template, dict) else {}

    def infer_execution_priority(
        self,
        severity: str | None,
        fallback: str | None = None,
    ) -> str | None:
        """Infer package priority from severity policy."""
        priority_map = self.policies.get("execution_priority_map", {})
        if not isinstance(priority_map, dict) or not severity:
            return fallback
        priority = priority_map.get(str(severity).strip().lower(), fallback)
        return str(priority) if priority is not None else fallback

    def infer_execution_mode(self, rule_type: str) -> str | None:
        """Infer execution mode from package policy."""
        mode_map = self.policies.get("default_execution_mode", {})
        if not isinstance(mode_map, dict):
            return None
        mode = mode_map.get(str(rule_type).strip().lower())
        return str(mode) if mode is not None else None

    def build_trace_metadata(
        self,
        index: int,
        profile_name: str | None,
        generated_at: str,
        trace_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build lightweight trace metadata for one package rule."""
        package_policy = self.policies.get("package_policy", {})
        include_trace_metadata = bool(
            package_policy.get("include_trace_metadata", True)
            if isinstance(package_policy, dict)
            else True
        )
        if not include_trace_metadata:
            return {}

        metadata: dict[str, Any] = {
            "input_rule_index": index,
            "source_profile": profile_name,
            "package_generated_at": generated_at,
        }
        if isinstance(trace_metadata, dict):
            metadata.update(trace_metadata)
        return metadata

    def build_execution_ready_rule(
        self,
        rule: ConfirmedQualityRule,
        index: int,
        profile_name: str | None,
        generated_at: str,
        trace_metadata: dict[str, Any] | None = None,
    ) -> ExecutionReadyRule:
        """Build one execution-ready rule from a confirmed quality rule."""
        template = self.map_rule_type_to_execution_template(rule.rule_type)
        package_policy = self.policies.get("package_policy", {})
        include_export_hints = bool(
            package_policy.get("include_export_hints", True)
            if isinstance(package_policy, dict)
            else True
        )
        engine_hints = template.get("engine_hints", {}) if include_export_hints else {}
        if not isinstance(engine_hints, dict):
            engine_hints = {}
        engine_hints = dict(engine_hints)
        engine_hints["dbt_native_compatible"] = bool(engine_hints.get("dbt")) and rule.rule_scope == "field"
        engine_hints["custom_only"] = not bool(engine_hints.get("dbt")) or rule.rule_scope == "cross_field"
        engine_hints["advisory_only"] = str(self.infer_execution_mode(rule.rule_type)) == "advisory_only"

        return ExecutionReadyRule(
            rule_id=self.build_rule_id(rule),
            source_table_name=rule.source_table_name,
            source_field_name=rule.source_field_name,
            target_field_name=rule.recommended_field_name,
            rule_type=rule.rule_type,
            semantic_type=template.get("semantic_type"),
            rule_expression=rule.rule_expression,
            execution_expression=rule.rule_expression
            if rule.rule_scope == "cross_field" and rule.rule_expression
            else template.get("execution_expression")
            or rule.rule_expression,
            execution_mode=self.infer_execution_mode(rule.rule_type),
            severity=rule.severity,
            priority=rule.priority or self.infer_execution_priority(rule.severity),
            rule_scope=rule.rule_scope,
            field_group=list(rule.field_group),
            confidence=rule.confidence,
            review_priority=rule.review_priority,
            confirmation_source=rule.confirmation_source,
            match_basis=rule.match_basis,
            reason=rule.reason,
            engine_hints=engine_hints,
            trace_metadata=self.build_trace_metadata(
                index=index,
                profile_name=profile_name,
                generated_at=generated_at,
                trace_metadata=trace_metadata,
            ),
            notes=rule.notes,
        )

    @staticmethod
    def summarize_package(package: ExecutionReadyPackage) -> dict[str, object]:
        """Return a report-friendly package summary."""
        semantic_counts: dict[str, int] = {}
        mode_counts: dict[str, int] = {}
        severity_counts: dict[str, int] = {}
        field_rule_count = 0
        cross_field_rule_count = 0
        non_native_rule_count = 0
        for rule in package.rules:
            if rule.rule_scope == "cross_field":
                cross_field_rule_count += 1
            else:
                field_rule_count += 1
            if "dbt" not in rule.engine_hints:
                non_native_rule_count += 1
            semantic_key = rule.semantic_type or "unknown"
            mode_key = rule.execution_mode or "unknown"
            severity_key = rule.severity or "unknown"
            semantic_counts[semantic_key] = semantic_counts.get(semantic_key, 0) + 1
            mode_counts[mode_key] = mode_counts.get(mode_key, 0) + 1
            severity_counts[severity_key] = severity_counts.get(severity_key, 0) + 1
        return {
            "package_id": package.package_id,
            "package_name": package.package_name,
            "rule_count": package.rule_count,
            "field_rule_count": field_rule_count,
            "cross_field_rule_count": cross_field_rule_count,
            "non_native_rule_count": non_native_rule_count,
            "source_profile": package.source_profile,
            "compatibility": package.compatibility,
            "semantic_type_counts": semantic_counts,
            "execution_mode_counts": mode_counts,
            "severity_counts": severity_counts,
            "summary": package.summary,
        }

    def build_package(
        self,
        confirmed_quality_rules: list[ConfirmedQualityRule | dict[str, object]],
        profile_name: str | None = None,
        trace_metadata: dict[str, Any] | None = None,
        package_name: str | None = None,
    ) -> ExecutionReadyPackage:
        """Build an execution-ready package from confirmed quality rules only."""
        generated_at = _utc_now()
        confirmed_rules = [_coerce_confirmed_rule(rule) for rule in confirmed_quality_rules]
        execution_rules = [
            self.build_execution_ready_rule(
                rule=rule,
                index=index,
                profile_name=profile_name,
                generated_at=generated_at,
                trace_metadata=trace_metadata,
            )
            for index, rule in enumerate(confirmed_rules)
        ]
        package_id = self.build_package_id(execution_rules, profile_name)
        compatibility = self.policies.get("engine_compatibility", {})
        if not isinstance(compatibility, dict):
            compatibility = {}
        resolved_package_name = package_name or f"{profile_name or 'confirmed_quality_rules'}_package"
        summary = (
            f"Execution-ready package contains {len(execution_rules)} confirmed quality rules."
        )

        return ExecutionReadyPackage(
            package_id=package_id,
            generated_at=generated_at,
            package_name=resolved_package_name,
            rule_count=len(execution_rules),
            source_profile=profile_name,
            rules=execution_rules,
            compatibility=dict(compatibility),
            summary=summary,
        )


# TODO: add Great Expectations/Soda package adapters, domain-aware planning, and real execution runtime handoff after this contract stabilizes.

"""Lightweight YAML configuration loader for rule-based skills."""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@cache
def load_yaml_config(file_name: str) -> dict[str, Any]:
    """Load a YAML configuration file from the application config directory."""
    config_path = CONFIG_DIR / file_name
    with config_path.open("r", encoding="utf-8") as config_file:
        loaded = yaml.safe_load(config_file) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f"Configuration file must contain a mapping: {config_path}")

    return loaded


def get_naming_rules_config() -> dict[str, Any]:
    """Return naming rule configuration."""
    return load_yaml_config("naming_rules.yaml")


def get_technical_keywords_config() -> dict[str, Any]:
    """Return technical keyword configuration."""
    return load_yaml_config("technical_keywords.yaml")


def get_lifecycle_keywords_config() -> dict[str, Any]:
    """Return lifecycle keyword configuration."""
    return load_yaml_config("lifecycle_keywords.yaml")


def get_severity_rules_config() -> dict[str, Any]:
    """Return severity mapping configuration."""
    return load_yaml_config("severity_rules.yaml")


def get_stg_rules_config() -> dict[str, Any]:
    """Return STG structure suggestion rules."""
    return load_yaml_config("stg_rules.yaml")


def get_field_transform_rules_config() -> dict[str, Any]:
    """Return field transformation rules for STG suggestions."""
    return load_yaml_config("field_transform_rules.yaml")


def get_quality_rule_templates_config() -> dict[str, Any]:
    """Return quality rule templates for recommendation."""
    return load_yaml_config("quality_rule_templates.yaml")


def get_quality_rule_policies_config() -> dict[str, Any]:
    """Return quality rule policy mappings for recommendation."""
    return load_yaml_config("quality_rule_policies.yaml")


def get_execution_package_policies_config() -> dict[str, Any]:
    """Return execution-ready package policy mappings."""
    return load_yaml_config("execution_package_policies.yaml")


def get_rule_execution_templates_config() -> dict[str, Any]:
    """Return execution-ready rule semantic templates."""
    return load_yaml_config("rule_execution_templates.yaml")


def get_domain_rule_templates_config() -> dict[str, Any]:
    """Return domain-aware quality rule templates."""
    return load_yaml_config("domain_rule_templates.yaml")


def get_cross_field_rule_patterns_config() -> dict[str, Any]:
    """Return cross-field quality rule pattern definitions."""
    return load_yaml_config("cross_field_rule_patterns.yaml")


def get_quality_review_policies_config() -> dict[str, Any]:
    """Return quality rule confidence and review-priority policies."""
    return load_yaml_config("quality_review_policies.yaml")


def get_readiness_scoring_policies_config() -> dict[str, Any]:
    """Return governance readiness scoring policies."""
    return load_yaml_config("readiness_scoring_policies.yaml")


def get_governance_gap_taxonomy_config() -> dict[str, Any]:
    """Return governance gap taxonomy configuration."""
    return load_yaml_config("governance_gap_taxonomy.yaml")


def get_remediation_templates_config() -> dict[str, Any]:
    """Return governance remediation templates."""
    return load_yaml_config("remediation_templates.yaml")


def get_governance_backlog_policies_config() -> dict[str, Any]:
    """Return governance backlog generation and transition policies."""
    return load_yaml_config("governance_backlog_policies.yaml")


def get_backlog_status_templates_config() -> dict[str, Any]:
    """Return governance backlog status templates."""
    return load_yaml_config("backlog_status_templates.yaml")


def get_governance_portfolio_policies_config() -> dict[str, Any]:
    """Return governance portfolio summary policies."""
    return load_yaml_config("governance_portfolio_policies.yaml")


def get_backlog_sla_policies_config() -> dict[str, Any]:
    """Return backlog SLA and due-date policies."""
    return load_yaml_config("backlog_sla_policies.yaml")


def get_progress_snapshot_policies_config() -> dict[str, Any]:
    """Return progress snapshot policies."""
    return load_yaml_config("progress_snapshot_policies.yaml")


def get_governance_delivery_templates_config() -> dict[str, Any]:
    """Return governance delivery workbook template configuration."""
    return load_yaml_config("governance_delivery_templates.yaml")


def get_delivery_template_profiles_config() -> dict[str, Any]:
    """Return enterprise delivery template profile configuration."""
    return load_yaml_config("delivery_template_profiles.yaml")


def get_delivery_layout_specs_config() -> dict[str, Any]:
    """Return enterprise delivery layout specification configuration."""
    return load_yaml_config("delivery_layout_specs.yaml")


def get_delivery_bundle_variants_config() -> dict[str, Any]:
    """Return enterprise delivery bundle variant configuration."""
    return load_yaml_config("delivery_bundle_variants.yaml")


def get_confirmation_workbook_policies_config() -> dict[str, Any]:
    """Return confirmation workbook and delivery package policies."""
    return load_yaml_config("confirmation_workbook_policies.yaml")


def get_batch_processing_policies_config() -> dict[str, Any]:
    """Return batch processing policies."""
    return load_yaml_config("batch_processing_policies.yaml")


def get_incremental_rerun_policies_config() -> dict[str, Any]:
    """Return incremental rerun and fingerprint policies."""
    return load_yaml_config("incremental_rerun_policies.yaml")


def get_workbook_import_policies_config() -> dict[str, Any]:
    """Return confirmation workbook import policies."""
    return load_yaml_config("workbook_import_policies.yaml")


def get_workbook_column_aliases_config() -> dict[str, Any]:
    """Return confirmation workbook column aliases."""
    return load_yaml_config("workbook_column_aliases.yaml")


def get_domain_governance_packs_config() -> dict[str, Any]:
    """Return domain governance pack definitions."""
    return load_yaml_config("domain_governance_packs.yaml")


def get_project_template_profiles_config() -> dict[str, Any]:
    """Return project template profile definitions."""
    return load_yaml_config("project_template_profiles.yaml")


def get_domain_delivery_templates_config() -> dict[str, Any]:
    """Return domain delivery output defaults."""
    return load_yaml_config("domain_delivery_templates.yaml")


def get_intake_template_profiles_config() -> dict[str, Any]:
    """Return metadata intake template profiles."""
    return load_yaml_config("intake_template_profiles.yaml")


def get_intake_field_mapping_specs_config() -> dict[str, Any]:
    """Return metadata intake field mapping specs."""
    return load_yaml_config("intake_field_mapping_specs.yaml")


def get_intake_diagnosis_policies_config() -> dict[str, Any]:
    """Return metadata intake diagnosis policies."""
    return load_yaml_config("intake_diagnosis_policies.yaml")


def get_confirmation_workbook_template_profiles_config() -> dict[str, Any]:
    """Return confirmation workbook template profiles."""
    return load_yaml_config("confirmation_workbook_template_profiles.yaml")


def get_confirmation_workbook_mapping_specs_config() -> dict[str, Any]:
    """Return confirmation workbook template mapping specs."""
    return load_yaml_config("confirmation_workbook_mapping_specs.yaml")


def get_confirmation_workbook_diagnosis_policies_config() -> dict[str, Any]:
    """Return confirmation workbook template diagnosis policies."""
    return load_yaml_config("confirmation_workbook_diagnosis_policies.yaml")


def get_issue_severity(issue_type: str, default: str = "low") -> str:
    """Return severity for an issue type from configuration."""
    severity_config = get_severity_rules_config()
    severity_mapping = severity_config.get("severity_mapping", {})
    configured_default = severity_config.get("default_severity", default)
    return str(severity_mapping.get(issue_type, configured_default))

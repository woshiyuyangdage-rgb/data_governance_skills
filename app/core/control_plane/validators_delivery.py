"""Delivery, workbook, batch, and incremental-rerun asset validators."""

from typing import Any

from app.core.models.validation_result import ValidationResult


def _validate_governance_delivery_templates(content: Any) -> ValidationResult:
    asset_name = "governance_delivery_templates"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["governance_delivery_templates must be a mapping."],
        )
    templates = content.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append("governance_delivery_templates must contain non-empty templates.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)
    for template_name, payload in templates.items():
        if not isinstance(payload, dict):
            errors.append(f"template '{template_name}' must be a mapping.")
            continue
        include_columns = payload.get("include_columns")
        if not isinstance(include_columns, list) or not include_columns:
            errors.append(f"template '{template_name}' must define include_columns.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_confirmation_workbook_policies(content: Any) -> ValidationResult:
    asset_name = "confirmation_workbook_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["confirmation_workbook_policies must be a mapping."],
        )
    if not isinstance(content.get("workbook_policy"), dict):
        errors.append("confirmation_workbook_policies must contain workbook_policy.")
    if not isinstance(content.get("delivery_package_policy"), dict):
        errors.append(
            "confirmation_workbook_policies must contain delivery_package_policy."
        )
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_batch_processing_policies(content: Any) -> ValidationResult:
    asset_name = "batch_processing_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["batch_processing_policies must be a mapping."],
        )
    if not isinstance(content.get("batch_policy"), dict):
        errors.append("batch_processing_policies must contain batch_policy.")
    supported_group_fields = content.get("supported_group_fields")
    if not isinstance(supported_group_fields, list) or not supported_group_fields:
        errors.append("batch_processing_policies supported_group_fields cannot be empty.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_incremental_rerun_policies(content: Any) -> ValidationResult:
    asset_name = "incremental_rerun_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["incremental_rerun_policies must be a mapping."],
        )
    if not isinstance(content.get("fingerprint_policy"), dict):
        errors.append("incremental_rerun_policies must contain fingerprint_policy.")
    diff_categories = content.get("diff_categories")
    if not isinstance(diff_categories, list) or not diff_categories:
        errors.append("incremental_rerun_policies diff_categories cannot be empty.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_workbook_import_policies(content: Any) -> ValidationResult:
    asset_name = "workbook_import_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["workbook_import_policies must be a mapping."],
        )
    if not isinstance(content.get("workbook_types"), dict) or not content.get("workbook_types"):
        errors.append("workbook_import_policies must contain workbook_types.")
    if not isinstance(content.get("confirmation_status_mapping"), dict) or not content.get("confirmation_status_mapping"):
        errors.append("workbook_import_policies must contain confirmation_status_mapping.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_workbook_column_aliases(content: Any) -> ValidationResult:
    asset_name = "workbook_column_aliases"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["workbook_column_aliases must be a mapping."],
        )
    aliases = content.get("aliases")
    if not isinstance(aliases, dict) or not aliases:
        errors.append("workbook_column_aliases aliases cannot be empty.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

DELIVERY_VALIDATORS = {
    "governance_delivery_templates": _validate_governance_delivery_templates,
    "confirmation_workbook_policies": _validate_confirmation_workbook_policies,
    "batch_processing_policies": _validate_batch_processing_policies,
    "incremental_rerun_policies": _validate_incremental_rerun_policies,
    "workbook_import_policies": _validate_workbook_import_policies,
    "workbook_column_aliases": _validate_workbook_column_aliases,
}

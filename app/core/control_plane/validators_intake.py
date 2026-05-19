"""Domain, project-template, intake, and confirmation-template asset validators."""

from typing import Any

from app.core.models.validation_result import ValidationResult


def _validate_domain_governance_packs(content: Any) -> ValidationResult:
    asset_name = "domain_governance_packs"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["domain_governance_packs must be a mapping."])
    packs = content.get("packs")
    if not isinstance(packs, list) or not packs:
        errors.append("domain_governance_packs packs cannot be empty.")
    elif isinstance(packs, list):
        for index, pack in enumerate(packs):
            if not isinstance(pack, dict):
                errors.append(f"pack at index {index} must be a mapping.")
                continue
            for field_name in ["pack_name", "enabled", "trigger_tokens"]:
                if field_name not in pack:
                    errors.append(f"pack at index {index} is missing '{field_name}'.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_project_template_profiles(content: Any) -> ValidationResult:
    asset_name = "project_template_profiles"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["project_template_profiles must be a mapping."])
    templates = content.get("templates")
    if not isinstance(templates, list) or not templates:
        errors.append("project_template_profiles templates cannot be empty.")
    elif isinstance(templates, list):
        for index, template in enumerate(templates):
            if not isinstance(template, dict):
                errors.append(f"template at index {index} must be a mapping.")
                continue
            for field_name in ["template_name", "enabled", "base_workflow_profile"]:
                if field_name not in template:
                    errors.append(f"template at index {index} is missing '{field_name}'.")
            if not str(template.get("base_workflow_profile", "")).strip():
                errors.append(f"template at index {index} must define base_workflow_profile.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_domain_delivery_templates(content: Any) -> ValidationResult:
    asset_name = "domain_delivery_templates"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["domain_delivery_templates must be a mapping."])
    defaults = content.get("delivery_defaults")
    if not isinstance(defaults, dict) or not defaults:
        errors.append("domain_delivery_templates delivery_defaults cannot be empty.")
    elif isinstance(defaults, dict):
        for pack_name, payload in defaults.items():
            if not isinstance(payload, dict):
                errors.append(f"delivery defaults for {pack_name} must be a mapping.")
                continue
            outputs = payload.get("include_outputs")
            if not isinstance(outputs, list) or not outputs:
                errors.append(f"delivery defaults for {pack_name} must contain include_outputs.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_intake_template_profiles(content: Any) -> ValidationResult:
    asset_name = "intake_template_profiles"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["intake_template_profiles must be a mapping."])
    profiles = content.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append("intake_template_profiles profiles cannot be empty.")
    elif isinstance(profiles, list):
        for index, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                errors.append(f"profile at index {index} must be a mapping.")
                continue
            for field_name in ["profile_name", "enabled", "required_target_fields", "mapping_spec_name"]:
                if field_name not in profile:
                    errors.append(f"profile at index {index} is missing '{field_name}'.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_intake_field_mapping_specs(content: Any) -> ValidationResult:
    asset_name = "intake_field_mapping_specs"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["intake_field_mapping_specs must be a mapping."])
    specs = content.get("mapping_specs")
    if not isinstance(specs, dict) or not specs:
        errors.append("intake_field_mapping_specs mapping_specs cannot be empty.")
    elif isinstance(specs, dict):
        for spec_name, mapping in specs.items():
            if not isinstance(mapping, dict) or not mapping:
                errors.append(f"mapping spec {spec_name} must be a non-empty mapping.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_intake_diagnosis_policies(content: Any) -> ValidationResult:
    asset_name = "intake_diagnosis_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=["intake_diagnosis_policies must be a mapping."])
    for field_name in ["diagnosis_policy", "matching_policy", "validation_policy"]:
        if not isinstance(content.get(field_name), dict) or not content.get(field_name):
            errors.append(f"intake_diagnosis_policies must contain {field_name}.")
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_confirmation_workbook_template_profiles(content: Any) -> ValidationResult:
    asset_name = "confirmation_workbook_template_profiles"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["confirmation_workbook_template_profiles must be a mapping."],
        )
    profiles = content.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append("confirmation_workbook_template_profiles profiles cannot be empty.")
    elif isinstance(profiles, list):
        for index, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                errors.append(f"profile at index {index} must be a mapping.")
                continue
            for field_name in ["template_name", "enabled", "workbook_type", "mapping_spec_name"]:
                if field_name not in profile:
                    errors.append(f"profile at index {index} is missing '{field_name}'.")
            if not isinstance(profile.get("required_target_fields"), list):
                errors.append(
                    f"profile at index {index} must define required_target_fields as a list."
                )
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_confirmation_workbook_mapping_specs(content: Any) -> ValidationResult:
    asset_name = "confirmation_workbook_mapping_specs"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["confirmation_workbook_mapping_specs must be a mapping."],
        )
    specs = content.get("mapping_specs")
    if not isinstance(specs, dict) or not specs:
        errors.append("confirmation_workbook_mapping_specs mapping_specs cannot be empty.")
    elif isinstance(specs, dict):
        for spec_name, mapping in specs.items():
            if not isinstance(mapping, dict) or not mapping:
                errors.append(f"mapping spec {spec_name} must be a non-empty mapping.")
                continue
            for target_field, aliases in mapping.items():
                if not str(target_field).strip():
                    errors.append(f"mapping spec {spec_name} contains an empty target field.")
                if not isinstance(aliases, list) or not aliases:
                    errors.append(
                        f"mapping spec {spec_name}.{target_field} must contain aliases."
                    )
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_confirmation_workbook_diagnosis_policies(content: Any) -> ValidationResult:
    asset_name = "confirmation_workbook_diagnosis_policies"
    errors: list[str] = []
    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["confirmation_workbook_diagnosis_policies must be a mapping."],
        )
    for field_name in ["diagnosis_policy", "matching_policy", "validation_policy"]:
        if not isinstance(content.get(field_name), dict) or not content.get(field_name):
            errors.append(
                f"confirmation_workbook_diagnosis_policies must contain {field_name}."
            )
    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

INTAKE_VALIDATORS = {
    "domain_governance_packs": _validate_domain_governance_packs,
    "project_template_profiles": _validate_project_template_profiles,
    "domain_delivery_templates": _validate_domain_delivery_templates,
    "intake_template_profiles": _validate_intake_template_profiles,
    "intake_field_mapping_specs": _validate_intake_field_mapping_specs,
    "intake_diagnosis_policies": _validate_intake_diagnosis_policies,
    "confirmation_workbook_template_profiles": _validate_confirmation_workbook_template_profiles,
    "confirmation_workbook_mapping_specs": _validate_confirmation_workbook_mapping_specs,
    "confirmation_workbook_diagnosis_policies": _validate_confirmation_workbook_diagnosis_policies,
}

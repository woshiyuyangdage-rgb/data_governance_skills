"""Quality-rule and execution-package asset validators."""

from typing import Any

from app.core.models.validation_result import ValidationResult


def _validate_quality_rule_templates(content: Any) -> ValidationResult:
    asset_name = "quality_rule_templates"
    errors: list[str] = []
    allowed_severities = {"high", "medium", "low"}

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["quality_rule_templates must be a mapping."],
        )

    templates = content.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append("quality_rule_templates must contain a non-empty 'templates' mapping.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for template_name, rule_list in templates.items():
        if not isinstance(rule_list, list) or not rule_list:
            errors.append(f"template '{template_name}' must contain a non-empty rule list.")
            continue
        for index, rule in enumerate(rule_list):
            if not isinstance(rule, dict):
                errors.append(f"template '{template_name}' rule at index {index} must be a mapping.")
                continue
            if not str(rule.get("rule_type", "")).strip():
                errors.append(
                    f"template '{template_name}' rule at index {index} must define rule_type."
                )
            severity = str(rule.get("severity", "")).strip().lower()
            if severity not in allowed_severities:
                errors.append(
                    f"template '{template_name}' rule at index {index} has invalid severity '{severity}'."
                )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_quality_rule_policies(content: Any) -> ValidationResult:
    asset_name = "quality_rule_policies"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["quality_rule_policies must be a mapping."],
        )

    required_mappings = [
        "token_to_template_map",
        "standard_code_to_template_map",
        "severity_default_priority_map",
        "recommendation_policy",
    ]
    for key in required_mappings:
        value = content.get(key)
        if not isinstance(value, dict):
            errors.append(f"quality_rule_policies must contain a '{key}' mapping.")
        elif not value and key == "recommendation_policy":
            errors.append("quality_rule_policies recommendation_policy cannot be empty.")
        elif not value:
            warnings.append(f"quality_rule_policies '{key}' is currently empty.")

    priority_map = content.get("severity_default_priority_map")
    if isinstance(priority_map, dict):
        for severity in priority_map:
            if str(severity).strip().lower() not in {"high", "medium", "low"}:
                errors.append(
                    f"severity_default_priority_map contains invalid severity '{severity}'."
                )

    token_map = content.get("token_to_template_map")
    if isinstance(token_map, dict):
        for key, value in token_map.items():
            if not str(key).strip() or not str(value).strip():
                errors.append("token_to_template_map contains an empty key or value.")

    standard_map = content.get("standard_code_to_template_map")
    if isinstance(standard_map, dict):
        for key, value in standard_map.items():
            if not str(key).strip() or not str(value).strip():
                errors.append(
                    "standard_code_to_template_map contains an empty key or value."
                )

    data_type_default_rules = content.get("data_type_default_rules")
    if not isinstance(data_type_default_rules, dict):
        errors.append("quality_rule_policies must contain a 'data_type_default_rules' mapping.")
    elif not data_type_default_rules:
        warnings.append("quality_rule_policies has an empty data_type_default_rules mapping.")
    else:
        for key, value in data_type_default_rules.items():
            if not isinstance(value, list):
                errors.append(
                    f"data_type_default_rules entry '{key}' must contain a list of template names."
                )

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )

def _validate_execution_package_policies(content: Any) -> ValidationResult:
    asset_name = "execution_package_policies"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["execution_package_policies must be a mapping."],
        )

    package_policy = content.get("package_policy")
    if not isinstance(package_policy, dict):
        errors.append("execution_package_policies must contain a package_policy mapping.")

    priority_map = content.get("execution_priority_map")
    if not isinstance(priority_map, dict) or not priority_map:
        errors.append(
            "execution_package_policies must contain a non-empty execution_priority_map mapping."
        )
    elif not {"high", "medium", "low"}.issubset(
        {str(key).strip().lower() for key in priority_map}
    ):
        warnings.append(
            "execution_priority_map should usually define high, medium, and low severities."
        )

    execution_modes = content.get("default_execution_mode")
    if not isinstance(execution_modes, dict) or not execution_modes:
        errors.append(
            "execution_package_policies must contain a non-empty default_execution_mode mapping."
        )

    compatibility = content.get("engine_compatibility")
    if not isinstance(compatibility, dict) or not compatibility:
        errors.append(
            "execution_package_policies must contain a non-empty engine_compatibility mapping."
        )
    elif not any(
        isinstance(payload, dict) and bool(payload.get("enabled", False))
        for payload in compatibility.values()
    ):
        warnings.append("engine_compatibility currently has no enabled engines.")

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )

def _validate_rule_execution_templates(content: Any) -> ValidationResult:
    asset_name = "rule_execution_templates"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["rule_execution_templates must be a mapping."],
        )

    templates = content.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append(
            "rule_execution_templates must contain a non-empty templates mapping."
        )
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for rule_type, template in templates.items():
        if not str(rule_type).strip():
            errors.append("rule_execution_templates contains an empty rule_type key.")
            continue
        if not isinstance(template, dict):
            errors.append(f"template '{rule_type}' must be a mapping.")
            continue
        if not str(template.get("semantic_type", "")).strip():
            errors.append(f"template '{rule_type}' must define semantic_type.")
        if not str(template.get("execution_expression", "")).strip():
            errors.append(f"template '{rule_type}' must define execution_expression.")
        engine_hints = template.get("engine_hints")
        if engine_hints is not None and not isinstance(engine_hints, dict):
            errors.append(f"template '{rule_type}' engine_hints must be a mapping.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_domain_rule_templates(content: Any) -> ValidationResult:
    asset_name = "domain_rule_templates"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["domain_rule_templates must be a mapping."],
        )

    domains = content.get("domains")
    if not isinstance(domains, dict) or not domains:
        errors.append("domain_rule_templates must contain a non-empty domains mapping.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for domain_name, payload in domains.items():
        if not isinstance(payload, dict):
            errors.append(f"domain '{domain_name}' must be a mapping.")
            continue
        trigger_tokens = payload.get("trigger_tokens")
        if not isinstance(trigger_tokens, list) or not trigger_tokens:
            errors.append(f"domain '{domain_name}' must define non-empty trigger_tokens.")
        rules = payload.get("rules")
        if not isinstance(rules, list) or not rules:
            errors.append(f"domain '{domain_name}' must define a non-empty rules list.")
            continue
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                errors.append(f"domain '{domain_name}' rule {index} must be a mapping.")
                continue
            if not str(rule.get("rule_type", "")).strip():
                errors.append(f"domain '{domain_name}' rule {index} must define rule_type.")
            required_tokens = rule.get("required_tokens")
            if not isinstance(required_tokens, list) or not required_tokens:
                errors.append(
                    f"domain '{domain_name}' rule {index} must define required_tokens."
                )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_cross_field_rule_patterns(content: Any) -> ValidationResult:
    asset_name = "cross_field_rule_patterns"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["cross_field_rule_patterns must be a mapping."],
        )

    patterns = content.get("patterns")
    if not isinstance(patterns, list) or not patterns:
        errors.append("cross_field_rule_patterns must contain a non-empty patterns list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for index, pattern in enumerate(patterns):
        if not isinstance(pattern, dict):
            errors.append(f"pattern at index {index} must be a mapping.")
            continue
        if not str(pattern.get("pattern_name", "")).strip():
            errors.append(f"pattern at index {index} must define pattern_name.")
        if not str(pattern.get("rule_type", "")).strip():
            errors.append(f"pattern at index {index} must define rule_type.")
        if not str(pattern.get("expression_template", "")).strip():
            errors.append(f"pattern at index {index} must define expression_template.")
        trigger_fields = pattern.get("trigger_fields")
        trigger_tokens = pattern.get("trigger_tokens")
        if not isinstance(trigger_fields, list) and not isinstance(trigger_tokens, list):
            errors.append(
                f"pattern at index {index} must define trigger_fields or trigger_tokens."
            )
        if isinstance(trigger_fields, list) and not trigger_fields:
            errors.append(f"pattern at index {index} has empty trigger_fields.")
        if isinstance(trigger_tokens, list) and not trigger_tokens:
            errors.append(f"pattern at index {index} has empty trigger_tokens.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

def _validate_quality_review_policies(content: Any) -> ValidationResult:
    asset_name = "quality_review_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["quality_review_policies must be a mapping."],
        )

    review_priority = content.get("review_priority")
    confidence_policy = content.get("confidence_policy")
    if not isinstance(review_priority, dict) or not review_priority:
        errors.append("quality_review_policies must contain review_priority.")
    if not isinstance(confidence_policy, dict) or not confidence_policy:
        errors.append("quality_review_policies must contain confidence_policy.")
    elif not all(
        isinstance(value, (int, float)) for value in confidence_policy.values()
    ):
        errors.append("quality_review_policies confidence_policy values must be numeric.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)

QUALITY_VALIDATORS = {
    "quality_rule_templates": _validate_quality_rule_templates,
    "quality_rule_policies": _validate_quality_rule_policies,
    "execution_package_policies": _validate_execution_package_policies,
    "rule_execution_templates": _validate_rule_execution_templates,
    "domain_rule_templates": _validate_domain_rule_templates,
    "cross_field_rule_patterns": _validate_cross_field_rule_patterns,
    "quality_review_policies": _validate_quality_review_policies,
}

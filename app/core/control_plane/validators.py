"""Validation rules for control plane managed assets."""

from typing import Any

from app.core.models.validation_result import ValidationResult


def _records_from_content(content: Any) -> list[dict[str, Any]]:
    if isinstance(content, list):
        return [record if isinstance(record, dict) else {"value": record} for record in content]
    raise ValueError("CSV content must be a list of row dictionaries.")


def _validate_workflow_profiles(content: Any) -> ValidationResult:
    asset_name = "workflow_profiles"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["workflow_profiles must be a mapping."],
            warnings=[],
        )

    profiles = content.get("profiles")
    if not isinstance(profiles, list):
        errors.append("workflow_profiles must contain a 'profiles' list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    names: list[str] = []
    for index, profile in enumerate(profiles):
        if not isinstance(profile, dict):
            errors.append(f"profile at index {index} must be a mapping.")
            continue
        for field_name in ["name", "enabled", "stages"]:
            if field_name not in profile:
                errors.append(f"profile at index {index} is missing '{field_name}'.")
        name = str(profile.get("name", "")).strip()
        if name:
            names.append(name)
        stages = profile.get("stages", [])
        if "stages" in profile and not isinstance(stages, list):
            errors.append(f"profile '{name or index}' must contain a stages list.")
        elif isinstance(stages, list) and not stages:
            warnings.append(f"profile '{name or index}' has an empty stages list.")

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        errors.append(
            f"workflow profile names must be unique: {', '.join(duplicate_names)}"
        )

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )


def _validate_intent_patterns(content: Any) -> ValidationResult:
    asset_name = "intent_patterns"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["intent_patterns must be a mapping."],
            warnings=[],
        )

    intents = content.get("intents")
    parameters = content.get("parameters")
    if not isinstance(intents, dict):
        errors.append("intent_patterns must contain an 'intents' mapping.")
    if not isinstance(parameters, dict):
        errors.append("intent_patterns must contain a 'parameters' mapping.")

    if isinstance(intents, dict):
        for intent_name, payload in intents.items():
            if not isinstance(payload, dict):
                errors.append(f"intent '{intent_name}' must be a mapping.")
                continue
            if not str(payload.get("profile_name", "")).strip():
                errors.append(f"intent '{intent_name}' must define profile_name.")
            keywords = payload.get("keywords")
            if not isinstance(keywords, list):
                errors.append(f"intent '{intent_name}' must define a keywords list.")
            elif not keywords:
                errors.append(f"intent '{intent_name}' must contain at least one keyword.")

    if isinstance(parameters, dict):
        for parameter_name, payload in parameters.items():
            if not isinstance(payload, dict):
                errors.append(f"parameter '{parameter_name}' must be a mapping.")
                continue
            keywords = payload.get("keywords")
            if not isinstance(keywords, list):
                errors.append(
                    f"parameter '{parameter_name}' must define a keywords list."
                )
            elif not keywords:
                warnings.append(
                    f"parameter '{parameter_name}' currently has no configured keywords."
                )

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )


def _validate_tool_registry(content: Any) -> ValidationResult:
    asset_name = "tool_registry"
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["tool_registry must be a mapping."],
            warnings=[],
        )

    tools = content.get("tools")
    if not isinstance(tools, list):
        errors.append("tool_registry must contain a 'tools' list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    names: list[str] = []
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            errors.append(f"tool at index {index} must be a mapping.")
            continue
        for field_name in ["name", "handler", "enabled"]:
            if field_name not in tool:
                errors.append(f"tool at index {index} is missing '{field_name}'.")
        name = str(tool.get("name", "")).strip()
        if name:
            names.append(name)
        if not str(tool.get("handler", "")).strip():
            errors.append(f"tool '{name or index}' must define a non-empty handler.")

    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    if duplicate_names:
        errors.append(f"tool names must be unique: {', '.join(duplicate_names)}")

    return ValidationResult(
        asset_name=asset_name,
        is_valid=not errors,
        messages=errors,
        warnings=warnings,
    )


def _validate_abbreviation_dict(content: Any) -> ValidationResult:
    asset_name = "abbreviation_dict"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["abbreviation_dict cannot be empty."],
        )

    required_columns = {"abbreviation", "expanded_form"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"abbreviation_dict is missing required columns: {', '.join(missing)}"
        )
    for index, record in enumerate(records):
        if not str(record.get("abbreviation", "")).strip():
            errors.append(f"row {index} has an empty abbreviation value.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_root_word_dict(content: Any) -> ValidationResult:
    asset_name = "root_word_dict"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["root_word_dict cannot be empty."],
        )

    required_columns = {"token", "normalized_form"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"root_word_dict is missing required columns: {', '.join(missing)}"
        )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_standard_fields(content: Any) -> ValidationResult:
    asset_name = "standard_fields"
    errors: list[str] = []
    records = _records_from_content(content)
    if not records:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["standard_fields cannot be empty."],
        )

    required_columns = {"standard_code", "standard_name", "standard_name_cn"}
    available_columns = set(records[0].keys())
    missing = sorted(required_columns - available_columns)
    if missing:
        errors.append(
            f"standard_fields is missing required columns: {', '.join(missing)}"
        )

    standard_codes: list[str] = []
    for index, record in enumerate(records):
        code = str(record.get("standard_code", "")).strip()
        if not code:
            errors.append(f"row {index} has an empty standard_code value.")
        else:
            standard_codes.append(code)

    duplicate_codes = sorted(
        {code for code in standard_codes if standard_codes.count(code) > 1}
    )
    if duplicate_codes:
        errors.append(
            f"standard_fields standard_code values must be unique: {', '.join(duplicate_codes)}"
        )

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


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


def _validate_readiness_scoring_policies(content: Any) -> ValidationResult:
    asset_name = "readiness_scoring_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["readiness_scoring_policies must be a mapping."],
        )

    dimensions = content.get("dimensions")
    thresholds = content.get("thresholds")
    scoring_rules = content.get("scoring_rules")
    if not isinstance(dimensions, dict) or not dimensions:
        errors.append("readiness_scoring_policies must contain dimensions.")
    else:
        for dimension_name, payload in dimensions.items():
            if not isinstance(payload, dict):
                errors.append(f"dimension '{dimension_name}' must be a mapping.")
                continue
            weight = payload.get("weight")
            if not isinstance(weight, (int, float)):
                errors.append(f"dimension '{dimension_name}' must define numeric weight.")
    if not isinstance(thresholds, dict) or not thresholds:
        errors.append("readiness_scoring_policies must contain thresholds.")
    elif "ready" not in thresholds or "partially_ready" not in thresholds:
        errors.append("thresholds must include ready and partially_ready.")
    if not isinstance(scoring_rules, dict) or not scoring_rules:
        errors.append("readiness_scoring_policies must contain scoring_rules.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_governance_gap_taxonomy(content: Any) -> ValidationResult:
    asset_name = "governance_gap_taxonomy"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["governance_gap_taxonomy must be a mapping."],
        )

    gaps = content.get("gaps")
    if not isinstance(gaps, list) or not gaps:
        errors.append("governance_gap_taxonomy must contain a non-empty gaps list.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for index, gap in enumerate(gaps):
        if not isinstance(gap, dict):
            errors.append(f"gap at index {index} must be a mapping.")
            continue
        if not str(gap.get("gap_type", "")).strip():
            errors.append(f"gap at index {index} must define gap_type.")
        if not str(gap.get("category", "")).strip():
            errors.append(f"gap at index {index} must define category.")
        sources = gap.get("sources")
        if not isinstance(sources, list) or not sources:
            errors.append(f"gap at index {index} must define non-empty sources.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_remediation_templates(content: Any) -> ValidationResult:
    asset_name = "remediation_templates"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["remediation_templates must be a mapping."],
        )

    templates = content.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append("remediation_templates must contain a non-empty templates mapping.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)

    for gap_type, template in templates.items():
        if not str(gap_type).strip():
            errors.append("remediation_templates contains an empty gap_type key.")
            continue
        if not isinstance(template, dict):
            errors.append(f"template '{gap_type}' must be a mapping.")
            continue
        if not str(template.get("action", "")).strip():
            errors.append(f"template '{gap_type}' must define action.")
        if not str(template.get("owner_role", "")).strip():
            errors.append(f"template '{gap_type}' must define owner_role.")
        if not str(template.get("expected_output", "")).strip():
            errors.append(f"template '{gap_type}' should define expected_output.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_governance_backlog_policies(content: Any) -> ValidationResult:
    asset_name = "governance_backlog_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["governance_backlog_policies must be a mapping."],
        )

    backlog_policy = content.get("backlog_policy")
    transition_policy = content.get("status_transition_policy")
    priority_mapping = content.get("priority_mapping")
    if not isinstance(backlog_policy, dict) or not backlog_policy:
        errors.append("governance_backlog_policies must contain backlog_policy.")
    if not isinstance(transition_policy, dict):
        errors.append(
            "governance_backlog_policies must contain status_transition_policy."
        )
    else:
        transitions = transition_policy.get("allowed_transitions")
        if not isinstance(transitions, dict) or not transitions:
            errors.append("status_transition_policy must contain allowed_transitions.")
    if not isinstance(priority_mapping, dict) or not priority_mapping:
        errors.append("governance_backlog_policies must contain priority_mapping.")
    else:
        for priority, payload in priority_mapping.items():
            if not isinstance(payload, dict):
                errors.append(f"priority '{priority}' must be a mapping.")
                continue
            if not isinstance(payload.get("urgency_score"), (int, float)):
                errors.append(f"priority '{priority}' must define urgency_score.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_backlog_status_templates(content: Any) -> ValidationResult:
    asset_name = "backlog_status_templates"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["backlog_status_templates must be a mapping."],
        )

    statuses = content.get("statuses")
    if not isinstance(statuses, dict) or not statuses:
        errors.append("backlog_status_templates must contain non-empty statuses.")
        return ValidationResult(asset_name=asset_name, is_valid=False, messages=errors)
    for status, payload in statuses.items():
        if not str(status).strip():
            errors.append("backlog_status_templates contains an empty status key.")
        if not isinstance(payload, dict):
            errors.append(f"status '{status}' must be a mapping.")
            continue
        if not str(payload.get("description", "")).strip():
            errors.append(f"status '{status}' must define description.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_governance_portfolio_policies(content: Any) -> ValidationResult:
    asset_name = "governance_portfolio_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["governance_portfolio_policies must be a mapping."],
        )

    dimensions = content.get("portfolio_dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        errors.append("governance_portfolio_policies must contain dimensions.")
    summary_policy = content.get("summary_policy")
    if not isinstance(summary_policy, dict) or not summary_policy:
        errors.append("governance_portfolio_policies must contain summary_policy.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_backlog_sla_policies(content: Any) -> ValidationResult:
    asset_name = "backlog_sla_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["backlog_sla_policies must be a mapping."],
        )

    due_days = content.get("default_due_days_by_priority")
    if not isinstance(due_days, dict) or not due_days:
        errors.append("backlog_sla_policies must contain default_due_days_by_priority.")
    elif not all(isinstance(value, (int, float)) for value in due_days.values()):
        errors.append("default_due_days_by_priority values must be numeric.")

    overdue_policy = content.get("overdue_policy")
    if not isinstance(overdue_policy, dict) or not overdue_policy:
        errors.append("backlog_sla_policies must contain overdue_policy.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


def _validate_progress_snapshot_policies(content: Any) -> ValidationResult:
    asset_name = "progress_snapshot_policies"
    errors: list[str] = []

    if not isinstance(content, dict):
        return ValidationResult(
            asset_name=asset_name,
            is_valid=False,
            messages=["progress_snapshot_policies must be a mapping."],
        )

    snapshot_policy = content.get("snapshot_policy")
    trend_fields = content.get("trend_fields")
    if not isinstance(snapshot_policy, dict) or not snapshot_policy:
        errors.append("progress_snapshot_policies must contain snapshot_policy.")
    if not isinstance(trend_fields, list) or not trend_fields:
        errors.append("progress_snapshot_policies must contain trend_fields.")

    return ValidationResult(asset_name=asset_name, is_valid=not errors, messages=errors)


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


def validate_asset_content(asset_name: str, content: Any) -> ValidationResult:
    """Validate one managed asset by its asset name."""
    validators = {
        "workflow_profiles": _validate_workflow_profiles,
        "intent_patterns": _validate_intent_patterns,
        "tool_registry": _validate_tool_registry,
        "abbreviation_dict": _validate_abbreviation_dict,
        "root_word_dict": _validate_root_word_dict,
        "standard_fields": _validate_standard_fields,
        "quality_rule_templates": _validate_quality_rule_templates,
        "quality_rule_policies": _validate_quality_rule_policies,
        "execution_package_policies": _validate_execution_package_policies,
        "rule_execution_templates": _validate_rule_execution_templates,
        "domain_rule_templates": _validate_domain_rule_templates,
        "cross_field_rule_patterns": _validate_cross_field_rule_patterns,
        "quality_review_policies": _validate_quality_review_policies,
        "readiness_scoring_policies": _validate_readiness_scoring_policies,
        "governance_gap_taxonomy": _validate_governance_gap_taxonomy,
        "remediation_templates": _validate_remediation_templates,
        "governance_backlog_policies": _validate_governance_backlog_policies,
        "backlog_status_templates": _validate_backlog_status_templates,
        "governance_portfolio_policies": _validate_governance_portfolio_policies,
        "backlog_sla_policies": _validate_backlog_sla_policies,
        "progress_snapshot_policies": _validate_progress_snapshot_policies,
        "governance_delivery_templates": _validate_governance_delivery_templates,
        "confirmation_workbook_policies": _validate_confirmation_workbook_policies,
        "batch_processing_policies": _validate_batch_processing_policies,
        "incremental_rerun_policies": _validate_incremental_rerun_policies,
        "workbook_import_policies": _validate_workbook_import_policies,
        "workbook_column_aliases": _validate_workbook_column_aliases,
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
    validator = validators.get(asset_name)
    if validator is None:
        return ValidationResult(
            asset_name=asset_name,
            is_valid=True,
            messages=[],
            warnings=[f"No dedicated validator is registered for asset '{asset_name}'."],
        )
    return validator(content)

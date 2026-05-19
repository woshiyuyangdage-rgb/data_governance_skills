"""Readiness, remediation, backlog, and portfolio asset validators."""

from typing import Any

from app.core.models.validation_result import ValidationResult


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

GOVERNANCE_VALIDATORS = {
    "readiness_scoring_policies": _validate_readiness_scoring_policies,
    "governance_gap_taxonomy": _validate_governance_gap_taxonomy,
    "remediation_templates": _validate_remediation_templates,
    "governance_backlog_policies": _validate_governance_backlog_policies,
    "backlog_status_templates": _validate_backlog_status_templates,
    "governance_portfolio_policies": _validate_governance_portfolio_policies,
    "backlog_sla_policies": _validate_backlog_sla_policies,
    "progress_snapshot_policies": _validate_progress_snapshot_policies,
}

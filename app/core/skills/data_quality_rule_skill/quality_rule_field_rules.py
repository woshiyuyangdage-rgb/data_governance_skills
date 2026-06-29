"""Field-level quality rule recommendation helpers."""

import re

from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.normalize import (
    clean_text,
    expand_tokens_with_evidence,
    normalize_tokens,
    split_tokens,
)
from app.core.rules.config_loader import (
    get_execution_package_policies_config,
    get_issue_severity,
    get_quality_review_policies_config,
    get_quality_rule_policies_config,
    get_quality_rule_templates_config,
)

SAMPLE_VALUE_SPLIT_PATTERN = re.compile(r"[;|,\r\n]+")
EMPTY_SAMPLE_VALUES = {"", "nan", "none", "null"}
MAX_VALUE_SET_SAMPLE_VALUES = 12
MAX_SAMPLE_VALUE_LENGTH = 64


def build_template_lookup() -> dict[str, list[dict[str, object]]]:
    """Return configured template definitions keyed by template name."""
    config = get_quality_rule_templates_config()
    templates = config.get("templates", {})
    if not isinstance(templates, dict):
        return {}
    return {
        str(key).strip().lower(): [
            {
                "rule_type": str(item.get("rule_type", "")).strip(),
                "severity": str(item.get("severity", "low")).strip().lower(),
                "rule_expression": str(item.get("rule_expression", "")).strip() or None,
            }
            for item in value
            if isinstance(item, dict) and str(item.get("rule_type", "")).strip()
        ]
        for key, value in templates.items()
        if isinstance(value, list)
    }


def priority_for_severity(severity: str) -> str | None:
    """Return the configured default review priority for a severity."""
    policies = get_quality_rule_policies_config()
    priority_map = policies.get("severity_default_priority_map", {})
    return priority_map.get(severity.lower())


def confidence_policy() -> dict[str, float]:
    """Return configured confidence policy values."""
    policies = get_quality_review_policies_config()
    policy = policies.get("confidence_policy", {})
    if not isinstance(policy, dict):
        return {}
    return {
        str(key): float(value)
        for key, value in policy.items()
        if isinstance(value, (int, float))
    }


def compute_quality_rule_confidence(match_source: str) -> float:
    """Return deterministic confidence for the recommendation evidence type."""
    policy = confidence_policy()
    return float(
        {
            "confirmed_mapping": policy.get("exact_template_match", 1.0),
            "standard_mapping": policy.get("domain_token_match", 0.8),
            "confirmed_stg": policy.get("stg_name_match", 0.7),
            "stg_suggestion": policy.get("stg_name_match", 0.7),
            "source_field_fallback": policy.get("source_token_match", 0.6),
            "cross_field_pattern": policy.get("exact_template_match", 1.0),
            "domain_rule_template": policy.get("domain_token_match", 0.8),
            "weak_hint": policy.get("weak_hint_match", 0.4),
        }.get(match_source, policy.get("weak_hint_match", 0.4))
    )


def risk_level_for_severity(severity: str | None) -> str:
    """Map severity to a review-friendly risk level."""
    return {
        "high": "high",
        "medium": "medium",
        "low": "low",
    }.get(str(severity or "").strip().lower(), "medium")


def export_formats_for_rule(rule_scope: str, rule_type: str) -> list[str]:
    """Infer practical export targets for one recommended rule."""
    formats = ["excel_quality_rule_list", "json_rule_package", "governance_task"]
    templates = get_execution_package_policies_config()
    compatibility = templates.get("engine_compatibility", {})
    dbt_enabled = bool(
        compatibility.get("dbt", {}).get("enabled")
        if isinstance(compatibility, dict)
        and isinstance(compatibility.get("dbt", {}), dict)
        else False
    )
    dbt_native_types = {"not_null", "uniqueness", "value_set"}
    if dbt_enabled and str(rule_scope) == "field" and rule_type in dbt_native_types:
        formats.append("dbt_tests_yaml")
    if str(rule_scope) != "field" or rule_type not in dbt_native_types:
        formats.append("custom_sql_check")
    return formats


def rule_name_for(
    *,
    source_table_name: str,
    source_field_name: str,
    rule_type: str,
    rule_scope: str,
    field_group: list[str] | None = None,
    target_table_name: str | None = None,
    target_field_name: str | None = None,
) -> str:
    """Build a readable deterministic rule name."""
    scope = str(rule_scope or "field")
    if scope == "cross_table":
        target = (
            f"{target_table_name}.{target_field_name}"
            if target_table_name and target_field_name
            else "referenced master field"
        )
        return (
            f"{source_table_name}.{source_field_name} references {target}"
        )
    if scope == "cross_field":
        group = ", ".join(field_group or [source_field_name])
        return f"{source_table_name}: {rule_type} for {group}"
    return f"{source_table_name}.{source_field_name}: {rule_type}"


def rule_description_for(
    *,
    rule_type: str,
    rule_expression: str | None,
    reason: str | None,
) -> str:
    """Build a concise business-facing rule description."""
    expression = f" Expression: {rule_expression}." if rule_expression else ""
    reason_text = f" Basis: {reason}" if reason else ""
    return f"Recommended {rule_type} quality check.{expression}{reason_text}".strip()


def infer_review_priority(
    *,
    rule_scope: str,
    rule_type: str,
    confidence: float | None,
) -> str:
    """Infer review priority from confidence, scope, and rule type."""
    policies = get_quality_review_policies_config()
    priority_policy = policies.get("review_priority", {})
    if not isinstance(priority_policy, dict):
        priority_policy = {}
    low_threshold = float(priority_policy.get("low_confidence_threshold", 0.4))
    medium_threshold = float(priority_policy.get("medium_confidence_threshold", 0.7))
    normalized_type = str(rule_type or "").lower()
    if (
        bool(priority_policy.get("prioritize_manual_review_for_reference_hints", True))
        and "reference" in normalized_type
    ):
        return "manual_review_preferred"
    if confidence is not None and confidence <= low_threshold:
        return "high_review_priority"
    if str(rule_scope) in {"cross_field", "cross_table"} and bool(
        priority_policy.get("prioritize_cross_field_rules", True)
    ):
        if confidence is not None and confidence < medium_threshold:
            return "high_review_priority"
        return "medium_review_priority"
    if confidence is not None and confidence < medium_threshold:
        return "high_review_priority"
    return "standard_review_priority"


def field_key(table_name: str, field_name: str) -> str:
    """Build the common table-field lookup key."""
    return f"{table_name}.{field_name}"


def tokenize_name(name: str | None) -> tuple[list[str], list[str]]:
    """Clean, split, expand, and normalize a name-like value."""
    cleaned = clean_text(name or "", lower=False)
    tokens = split_tokens(cleaned)
    expanded_tokens, _, _ = expand_tokens_with_evidence(tokens)
    normalized_token_list = normalize_tokens(expanded_tokens)
    return tokens, normalized_token_list


def field_tokens(field_name: str) -> set[str]:
    """Return normalized field tokens with lightweight synonym expansion."""
    _, normalized_tokens = tokenize_name(field_name)
    tokens = {str(token).lower() for token in normalized_tokens}
    synonyms: dict[str, set[str]] = {
        "date": {"dt", "time", "timestamp"},
        "amount": {"amt", "value"},
        "currency": {"ccy", "curr"},
        "id": {"identifier"},
        "updated": {"update", "modified", "modify"},
        "created": {"create", "creation"},
    }
    expanded = set(tokens)
    for canonical, alternatives in synonyms.items():
        if canonical in tokens or tokens.intersection(alternatives):
            expanded.add(canonical)
    return expanded


def learning_context_for_field(
    *,
    field_name: str,
    data_type: str | None,
    recommended_field_name: str | None,
    recommendation_source: str,
    match_basis: str | None,
) -> list[str]:
    """Build stable association-rule items for one field-level recommendation."""
    context: list[str] = []
    if data_type:
        normalized_type = data_type.strip().lower().split("(", 1)[0]
        if normalized_type:
            context.append(f"type:{normalized_type}")

    for token in sorted(field_tokens(field_name)):
        context.append(f"token:{token}")

    for token in sorted(field_tokens(recommended_field_name or "")):
        context.append(f"field:{token}")

    if recommendation_source:
        context.append(f"source:{recommendation_source.strip().lower()}")

    if match_basis:
        basis_text = str(match_basis).strip().lower()
        if "standard_code=" in basis_text:
            context.append(f"basis:{basis_text.split('standard_code=', 1)[1]}")

    return list(dict.fromkeys(context))


def candidate_value_set_from_sample_values(sample_values: str | None) -> list[str]:
    """Infer a compact accepted-value set from source sample values."""
    if sample_values is None:
        return []

    text = str(sample_values).strip()
    if not text or text.lower() in EMPTY_SAMPLE_VALUES:
        return []

    values: list[str] = []
    seen: set[str] = set()
    for raw_value in SAMPLE_VALUE_SPLIT_PATTERN.split(text):
        value = raw_value.strip().strip("'\"")
        if not value or value.lower() in EMPTY_SAMPLE_VALUES:
            continue
        if len(value) > MAX_SAMPLE_VALUE_LENGTH:
            return []
        key = value.casefold()
        if key in seen:
            continue
        values.append(value)
        seen.add(key)

    if len(values) < 2 or len(values) > MAX_VALUE_SET_SAMPLE_VALUES:
        return []
    return values


def value_set_expression(values: list[str]) -> str:
    """Build a deterministic value-set expression for generated rules."""
    escaped_values = [value.replace("'", "''") for value in values]
    quoted_values = ", ".join(f"'{value}'" for value in escaped_values)
    return f"value in ({quoted_values})"


def table_tokens(table: TableMeta) -> set[str]:
    """Return normalized tokens collected from table and field metadata."""
    tokens: set[str] = set()
    for value in [table.table_name, table.table_description, table.table_name_cn]:
        _, normalized_tokens = tokenize_name(value)
        tokens.update(str(token).lower() for token in normalized_tokens)
    for field in table.fields:
        tokens.update(field_tokens(field.field_name))
    return tokens


def mapping_lookup(results: list[MappingResult]) -> dict[str, MappingResult]:
    """Build a table-field mapping result lookup."""
    return {field_key(item.table_name, item.field_name): item for item in results}


def stg_lookup(
    suggestions: list[StgFieldSuggestion],
) -> dict[str, StgFieldSuggestion]:
    """Build a table-field STG suggestion lookup."""
    return {
        field_key(item.source_table_name, item.source_field_name): item
        for item in suggestions
    }


def candidate_templates_from_standard_code(standard_code: str | None) -> list[str]:
    """Infer template names from a standard field code."""
    if not standard_code:
        return []
    policies = get_quality_rule_policies_config()
    mapping = policies.get("standard_code_to_template_map", {})
    matched = mapping.get(standard_code.strip().lower())
    return [str(matched).strip().lower()] if matched else []


def candidate_templates_from_tokens(tokens: list[str]) -> list[str]:
    """Infer template names from normalized tokens."""
    policies = get_quality_rule_policies_config()
    token_map = policies.get("token_to_template_map", {})
    matched: list[str] = []
    for token in tokens:
        template_name = token_map.get(token.strip().lower())
        if template_name:
            matched.append(str(template_name).strip().lower())
    return list(dict.fromkeys(matched))


def candidate_templates_from_data_type(data_type: str | None) -> list[str]:
    """Infer default template names from a data type."""
    if not data_type:
        return []
    policies = get_quality_rule_policies_config()
    normalized_type = data_type.strip().lower().split("(", 1)[0]
    mapping = policies.get("data_type_default_rules", {})
    candidates = mapping.get(normalized_type, [])
    if not isinstance(candidates, list):
        return []
    return [str(item).strip().lower() for item in candidates if str(item).strip()]


def infer_rule_templates_from_mapping(
    mapping_result: MappingResult | None,
) -> tuple[list[str], str | None, str | None]:
    """Infer templates from a mapping result."""
    if mapping_result is None:
        return [], None, None
    templates = candidate_templates_from_standard_code(
        mapping_result.recommended_standard_code
    )
    match_basis = None
    reason = None
    if templates:
        match_basis = f"standard_code={mapping_result.recommended_standard_code}"
        reason = (
            "Matched rule template from standard mapping "
            f"standard_code={mapping_result.recommended_standard_code}"
        )
    return templates, match_basis, reason


def infer_rule_templates_from_stg_name(
    stg_suggestion: StgFieldSuggestion | None,
    recommendation_source: str,
) -> tuple[list[str], str | None, str | None]:
    """Infer templates from an STG field suggestion name."""
    if stg_suggestion is None:
        return [], None, None
    _, normalized_tokens = tokenize_name(stg_suggestion.recommended_stg_field_name)
    templates = candidate_templates_from_tokens(normalized_tokens)
    if not templates:
        templates = candidate_templates_from_data_type(
            stg_suggestion.recommended_data_type
        )
    match_basis = None
    reason = None
    if templates:
        match_basis = (
            "recommended_stg_field_name="
            f"{stg_suggestion.recommended_stg_field_name}"
        )
        reason = (
            "Matched template from STG suggestion "
            f"{stg_suggestion.recommended_stg_field_name}"
        )
    elif stg_suggestion.recommended_data_type:
        match_basis = f"recommended_data_type={stg_suggestion.recommended_data_type}"
        reason = (
            "Matched fallback data-type template from STG suggestion "
            f"{stg_suggestion.recommended_data_type}"
        )
    if reason and recommendation_source == "confirmed_stg":
        reason = f"{reason} after confirmed STG review"
    return templates, match_basis, reason


def infer_rule_templates_from_source_name(
    field_name: str,
    data_type: str | None,
) -> tuple[list[str], str | None, str | None]:
    """Infer templates from source-field tokens and type."""
    _, normalized_tokens = tokenize_name(field_name)
    templates = candidate_templates_from_tokens(normalized_tokens)
    basis = None
    reason = None
    if templates:
        basis = f"source_field_name={field_name}"
        reason = f"Matched template from source field name {field_name}"
        return templates, basis, reason

    templates = candidate_templates_from_data_type(data_type)
    if templates:
        basis = f"source_data_type={data_type}"
        reason = f"Matched fallback data-type template from source_data_type={data_type}"
    return templates, basis, reason


def build_quality_rule_suggestion(
    source_table_name: str,
    source_field_name: str,
    source_data_type: str | None,
    recommended_field_name: str | None,
    recommendation_source: str,
    template_name: str,
    rule_template: dict[str, object],
    match_basis: str | None,
    reason: str | None,
    source_sample_values: str | None = None,
) -> QualityRuleSuggestion:
    """Create one normalized quality-rule suggestion."""
    severity = str(rule_template.get("severity", "low")).lower()
    rule_type = str(rule_template.get("rule_type", ""))
    confidence = compute_quality_rule_confidence(recommendation_source)
    rule_expression = rule_template.get("rule_expression")
    expression_text = str(rule_expression) if rule_expression is not None else None
    value_set_values = (
        candidate_value_set_from_sample_values(source_sample_values)
        if rule_type == "value_set"
        else []
    )
    if value_set_values:
        expression_text = value_set_expression(value_set_values)
        sample_reason = (
            "Derived accepted values from source sample_values "
            f"count={len(value_set_values)}"
        )
        reason = f"{reason}; {sample_reason}" if reason else sample_reason
    review_priority = infer_review_priority(
        rule_scope="field",
        rule_type=rule_type,
        confidence=confidence,
    )
    learning_context = learning_context_for_field(
        field_name=source_field_name,
        data_type=source_data_type,
        recommended_field_name=recommended_field_name,
        recommendation_source=recommendation_source,
        match_basis=match_basis,
    )
    if value_set_values:
        learning_context.append(f"value_set_size:{len(value_set_values)}")

    return QualityRuleSuggestion(
        source_table_name=source_table_name,
        source_field_name=source_field_name,
        rule_name=rule_name_for(
            source_table_name=source_table_name,
            source_field_name=source_field_name,
            rule_type=rule_type,
            rule_scope="field",
        ),
        rule_description=rule_description_for(
            rule_type=rule_type,
            rule_expression=expression_text,
            reason=reason,
        ),
        recommended_field_name=recommended_field_name,
        rule_type=rule_type,
        rule_expression=expression_text,
        severity=severity,
        priority=priority_for_severity(severity),
        risk_level=risk_level_for_severity(severity),
        confidence=confidence,
        requires_manual_review=review_priority != "standard_review_priority",
        review_priority=review_priority,
        rule_scope="field",
        field_group=[source_field_name],
        recommendation_source=recommendation_source,
        match_basis=match_basis,
        reason=reason,
        export_formats=export_formats_for_rule("field", rule_type),
        learning_context=learning_context,
        notes=(
            f"Recommended from template={template_name}. "
            f"sample_value_set={value_set_values}."
            if value_set_values
            else f"Recommended from template={template_name}."
        ),
    )


def deduplicate_rules_for_field(
    suggestions: list[QualityRuleSuggestion],
) -> list[QualityRuleSuggestion]:
    """Remove duplicate rule types for the same field while keeping first evidence."""
    deduped: list[QualityRuleSuggestion] = []
    seen: set[tuple[str, str, str]] = set()
    for suggestion in suggestions:
        key = (
            suggestion.source_table_name,
            suggestion.source_field_name,
            suggestion.rule_type,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(suggestion)
    return deduped


def build_quality_issue(
    issue_id: str,
    table_name: str,
    field_name: str,
    issue_type: str,
    evidence: list[str],
    suggestion: str,
    confidence: float,
) -> Issue:
    """Build a normalized quality-rule issue."""
    return Issue(
        issue_id=issue_id,
        object_type="field",
        object_name=f"{table_name}.{field_name}",
        issue_type=issue_type,
        severity=get_issue_severity(issue_type),
        evidence=evidence,
        suggestion=suggestion,
        confidence=confidence,
    )


def select_basis_for_field(
    *,
    table_name: str,
    field_name: str,
    data_type: str | None,
    effective_mappings: dict[str, MappingResult],
    fallback_mappings: dict[str, MappingResult],
    effective_stg: dict[str, StgFieldSuggestion],
    fallback_stg: dict[str, StgFieldSuggestion],
) -> tuple[list[str], str, str | None, str | None, str | None]:
    """Select the best recommendation basis for one source field."""
    lookup_key = field_key(table_name, field_name)

    mapping_result = effective_mappings.get(lookup_key)
    templates, match_basis, reason = infer_rule_templates_from_mapping(mapping_result)
    if templates:
        recommended_field_name = (
            mapping_result.recommended_standard_name
            or mapping_result.recommended_standard_code
        )
        return templates, "confirmed_mapping", recommended_field_name, match_basis, reason

    mapping_result = fallback_mappings.get(lookup_key)
    templates, match_basis, reason = infer_rule_templates_from_mapping(mapping_result)
    if templates:
        recommended_field_name = (
            mapping_result.recommended_standard_name
            or mapping_result.recommended_standard_code
        )
        return templates, "standard_mapping", recommended_field_name, match_basis, reason

    stg_suggestion = effective_stg.get(lookup_key)
    templates, match_basis, reason = infer_rule_templates_from_stg_name(
        stg_suggestion,
        "confirmed_stg",
    )
    if templates:
        return (
            templates,
            "confirmed_stg",
            stg_suggestion.recommended_stg_field_name,
            match_basis,
            reason,
        )

    stg_suggestion = fallback_stg.get(lookup_key)
    templates, match_basis, reason = infer_rule_templates_from_stg_name(
        stg_suggestion,
        "stg_suggestion",
    )
    if templates:
        return (
            templates,
            "stg_suggestion",
            stg_suggestion.recommended_stg_field_name,
            match_basis,
            reason,
        )

    templates, match_basis, reason = infer_rule_templates_from_source_name(
        field_name,
        data_type,
    )
    return templates, "source_field_fallback", field_name, match_basis, reason

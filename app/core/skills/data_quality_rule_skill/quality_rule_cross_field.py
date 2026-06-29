"""Cross-field and domain-aware helpers for quality rule recommendation."""

from collections import defaultdict
from collections.abc import Callable

from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import (
    get_cross_field_rule_patterns_config,
    get_domain_rule_templates_config,
)
from app.core.skills.data_quality_rule_skill.quality_rule_field_rules import (
    export_formats_for_rule,
    field_tokens,
    risk_level_for_severity,
    rule_description_for,
    rule_name_for,
)

BuildRule = Callable[..., CrossFieldQualityRule]
DeduplicateRules = Callable[[list[CrossFieldQualityRule]], list[CrossFieldQualityRule]]
FieldTokens = Callable[[str], set[str]]
FindField = Callable[[dict[str, set[str]], set[str]], str | None]
TableTokens = Callable[[TableMeta], set[str]]


def build_cross_field_rule(
    *,
    table_name: str,
    field_group: list[str],
    rule_type: str,
    rule_expression: str,
    severity: str,
    recommendation_source: str,
    match_basis: str,
    reason: str,
    confidence_source: str,
    priority_for_severity: Callable[[str], str | None],
    compute_quality_rule_confidence: Callable[[str], float],
    infer_review_priority: Callable[..., str],
    rule_scope: str = "cross_field",
    source_field_name: str | None = None,
    target_table_name: str | None = None,
    target_field_name: str | None = None,
    notes: str | None = None,
) -> CrossFieldQualityRule:
    """Build one normalized cross-field quality rule."""
    confidence = compute_quality_rule_confidence(confidence_source)
    primary_field = source_field_name or (field_group[0] if field_group else None)
    review_priority = infer_review_priority(
        rule_scope=rule_scope,
        rule_type=rule_type,
        confidence=confidence,
    )
    return CrossFieldQualityRule(
        source_table_name=table_name,
        source_field_name=primary_field,
        rule_name=rule_name_for(
            source_table_name=table_name,
            source_field_name=primary_field or "__rule__",
            rule_type=rule_type,
            rule_scope=rule_scope,
            field_group=field_group,
            target_table_name=target_table_name,
            target_field_name=target_field_name,
        ),
        rule_description=rule_description_for(
            rule_type=rule_type,
            rule_expression=rule_expression,
            reason=reason,
        ),
        target_table_name=target_table_name,
        target_field_name=target_field_name,
        field_group=list(dict.fromkeys(field_group)),
        rule_type=rule_type,
        rule_expression=rule_expression,
        severity=severity,
        priority=priority_for_severity(severity),
        risk_level=risk_level_for_severity(severity),
        confidence=confidence,
        requires_manual_review=True,
        review_priority=review_priority,
        rule_scope=rule_scope,
        recommendation_source=recommendation_source,
        match_basis=match_basis,
        reason=reason,
        export_formats=export_formats_for_rule(rule_scope, rule_type),
        notes=notes,
    )


def find_field_by_tokens(
    field_tokens: dict[str, set[str]],
    required_tokens: set[str],
) -> str | None:
    """Return the first field whose normalized tokens cover the required tokens."""
    for field_name, tokens in field_tokens.items():
        if required_tokens.issubset(tokens):
            return field_name
    return None


def detect_cross_field_patterns(
    *,
    table: TableMeta,
    field_tokens_for_name: FieldTokens,
    find_field: FindField,
    build_rule: BuildRule,
    deduplicate_rules: DeduplicateRules,
) -> list[CrossFieldQualityRule]:
    """Detect configured and built-in cross-field rules in one source table."""
    field_tokens = {
        field.field_name: field_tokens_for_name(field.field_name)
        for field in table.fields
    }
    rules: list[CrossFieldQualityRule] = []
    pattern_config = get_cross_field_rule_patterns_config()
    configured_patterns = pattern_config.get("patterns", [])
    if isinstance(configured_patterns, list):
        for pattern in configured_patterns:
            if not isinstance(pattern, dict):
                continue
            pattern_name = str(pattern.get("pattern_name", "")).strip()
            severity = str(pattern.get("severity", "medium")).lower()
            rule_type = str(pattern.get("rule_type", "")).strip()
            expression_template = str(pattern.get("expression_template", "")).strip()
            if not rule_type or not expression_template:
                continue

            matched_fields: list[str] = []
            trigger_fields = pattern.get("trigger_fields", [])
            if isinstance(trigger_fields, list) and trigger_fields:
                for trigger in trigger_fields:
                    trigger_tokens = field_tokens_for_name(str(trigger))
                    matched = find_field(field_tokens, trigger_tokens)
                    if matched:
                        matched_fields.append(matched)
            trigger_tokens = pattern.get("trigger_tokens", [])
            if isinstance(trigger_tokens, list) and trigger_tokens and not matched_fields:
                required = {str(token).lower() for token in trigger_tokens}
                for field_name, tokens in field_tokens.items():
                    if required.intersection(tokens):
                        matched_fields.append(field_name)

            if len(set(matched_fields)) < 2:
                continue

            rules.append(
                build_rule(
                    table_name=table.table_name,
                    field_group=list(dict.fromkeys(matched_fields)),
                    rule_type=rule_type,
                    rule_expression=expression_template,
                    severity=severity,
                    recommendation_source="cross_field_pattern",
                    match_basis=f"pattern={pattern_name}",
                    reason=(
                        f"Matched cross-field pattern '{pattern_name}' from fields "
                        f"{', '.join(dict.fromkeys(matched_fields))}."
                    ),
                    confidence_source="cross_field_pattern",
                    notes="Generated from cross_field_rule_patterns.yaml.",
                )
            )

    created = find_field(field_tokens, {"created", "date"})
    updated = find_field(field_tokens, {"updated", "date"})
    if created and updated:
        rules.append(
            build_rule(
                table_name=table.table_name,
                field_group=[created, updated],
                rule_type="temporal_order",
                rule_expression=f"{created} <= {updated}",
                severity="medium",
                recommendation_source="cross_field_pattern",
                match_basis="created_date/updated_date",
                reason="Created timestamp should not be later than updated timestamp.",
                confidence_source="cross_field_pattern",
            )
        )

    start = find_field(field_tokens, {"start", "date"})
    end = find_field(field_tokens, {"end", "date"})
    if start and end:
        rules.append(
            build_rule(
                table_name=table.table_name,
                field_group=[start, end],
                rule_type="temporal_order",
                rule_expression=f"{start} <= {end}",
                severity="medium",
                recommendation_source="cross_field_pattern",
                match_basis="start_date/end_date",
                reason="Start date should not be later than end date.",
                confidence_source="cross_field_pattern",
            )
        )

    amount = find_field(field_tokens, {"amount"})
    currency = find_field(field_tokens, {"currency"})
    if amount and currency:
        rules.append(
            build_rule(
                table_name=table.table_name,
                field_group=[amount, currency],
                rule_type="paired_presence",
                rule_expression=f"{amount} requires {currency}",
                severity="medium",
                recommendation_source="cross_field_pattern",
                match_basis="amount/currency",
                reason=(
                    "Amount fields should be interpreted with an associated "
                    "currency field."
                ),
                confidence_source="cross_field_pattern",
            )
        )

    status_code = find_field(field_tokens, {"status", "code"})
    status_name = find_field(field_tokens, {"status", "name"})
    if status_code and status_name:
        rules.append(
            build_rule(
                table_name=table.table_name,
                field_group=[status_code, status_name],
                rule_type="paired_presence",
                rule_expression=f"{status_code} pairs with {status_name}",
                severity="low",
                recommendation_source="cross_field_pattern",
                match_basis="status_code/status_name",
                reason="Status code and status name should be reviewed as a pair.",
                confidence_source="cross_field_pattern",
            )
        )

    fields_by_prefix: dict[str, dict[str, str]] = defaultdict(dict)
    for field_name, tokens in field_tokens.items():
        if "id" in tokens:
            prefix = field_name.lower().rsplit("id", 1)[0].strip("_-. ")
            fields_by_prefix[prefix]["id"] = field_name
        if "name" in tokens:
            prefix = field_name.lower().rsplit("name", 1)[0].strip("_-. ")
            fields_by_prefix[prefix]["name"] = field_name
    for prefix, pair in fields_by_prefix.items():
        if pair.get("id") and pair.get("name"):
            rules.append(
                build_rule(
                    table_name=table.table_name,
                    field_group=[pair["id"], pair["name"]],
                    rule_type="reference_consistency_hint",
                    rule_expression=(
                        f"{pair['id']} should be consistent with {pair['name']}"
                    ),
                    severity="low",
                    recommendation_source="weak_hint",
                    match_basis=f"id/name prefix={prefix or 'generic'}",
                    reason=(
                        "Identifier/name pairs often require reference "
                        "consistency review."
                    ),
                    confidence_source="weak_hint",
                )
            )

    return deduplicate_rules(rules)


def detect_domain_rule_candidates(
    *,
    table: TableMeta,
    table_tokens_for_table: TableTokens,
    field_tokens_for_name: FieldTokens,
    find_field: FindField,
    build_rule: BuildRule,
    deduplicate_rules: DeduplicateRules,
) -> list[CrossFieldQualityRule]:
    """Detect domain-aware single-table rule candidates from configured templates."""
    config = get_domain_rule_templates_config()
    domains = config.get("domains", {})
    if not isinstance(domains, dict):
        return []
    table_tokens = table_tokens_for_table(table)
    field_tokens = {
        field.field_name: field_tokens_for_name(field.field_name)
        for field in table.fields
    }
    rules: list[CrossFieldQualityRule] = []

    for domain_name, payload in domains.items():
        if not isinstance(payload, dict):
            continue
        trigger_tokens = {
            str(token).lower()
            for token in payload.get("trigger_tokens", [])
            if str(token).strip()
        }
        if trigger_tokens and not table_tokens.intersection(trigger_tokens):
            continue
        for template in payload.get("rules", []):
            if not isinstance(template, dict):
                continue
            required_tokens = [
                str(token).lower()
                for token in template.get("required_tokens", [])
                if str(token).strip()
            ]
            matched_fields: list[str] = []
            for token in required_tokens:
                matched = find_field(field_tokens, {token})
                if matched:
                    matched_fields.append(matched)
            if not matched_fields:
                continue

            rule_type = str(template.get("rule_type", "")).strip()
            severity = str(template.get("severity", "medium")).lower()
            if not rule_type:
                continue
            expression = (
                f"{domain_name} domain expects fields matching "
                f"{', '.join(required_tokens)}"
            )
            rules.append(
                build_rule(
                    table_name=table.table_name,
                    field_group=list(dict.fromkeys(matched_fields)),
                    rule_type=rule_type,
                    rule_expression=expression,
                    severity=severity,
                    recommendation_source="domain_rule_template",
                    match_basis=(
                        f"domain={domain_name}; "
                        f"required_tokens={','.join(required_tokens)}"
                    ),
                    reason=(
                        f"Matched domain-aware rule template for '{domain_name}' "
                        f"based on metadata tokens."
                    ),
                    confidence_source="domain_rule_template",
                    notes="Generated from domain_rule_templates.yaml.",
                )
            )

    return deduplicate_rules(rules)


def _reference_token(field_name: str) -> str:
    tokens = [
        token
        for token in field_tokens(field_name)
        if token
        and token not in {"id", "identifier", "number", "no", "code", "key"}
    ]
    return "_".join(sorted(tokens)) or field_name.lower().replace("_id", "").replace("_no", "")


def _primary_key_fields(table: TableMeta) -> list[str]:
    configured = [field for field in table.primary_key_fields if field]
    if configured:
        return configured
    return [field.field_name for field in table.fields if field.is_primary_key]


def _foreign_key_fields(table: TableMeta) -> list[str]:
    configured = [field for field in table.foreign_key_fields if field]
    if configured:
        return configured
    return [field.field_name for field in table.fields if field.is_foreign_key]


def detect_cross_table_reference_rules(
    *,
    tables: list[TableMeta],
    build_rule: BuildRule,
    deduplicate_rules: DeduplicateRules,
) -> list[CrossFieldQualityRule]:
    """Infer referential consistency hints from primary/foreign-key metadata."""
    primary_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for table in tables:
        for field_name in _primary_key_fields(table):
            primary_index[_reference_token(field_name)].append(
                (table.table_name, field_name)
            )

    rules: list[CrossFieldQualityRule] = []
    for table in tables:
        for field_name in _foreign_key_fields(table):
            candidates = [
                candidate
                for candidate in primary_index.get(_reference_token(field_name), [])
                if candidate[0] != table.table_name
            ]
            if not candidates:
                continue
            target_table, target_field = candidates[0]
            rules.append(
                build_rule(
                    table_name=table.table_name,
                    field_group=[field_name],
                    rule_type="cross_table_reference",
                    rule_expression=(
                        f"{table.table_name}.{field_name} exists in "
                        f"{target_table}.{target_field}"
                    ),
                    severity="medium",
                    recommendation_source="cross_table_reference_pattern",
                    match_basis=(
                        f"foreign_key={table.table_name}.{field_name}; "
                        f"primary_key={target_table}.{target_field}"
                    ),
                    reason=(
                        "Foreign-key metadata indicates this field should resolve "
                        "to a master or parent table identifier."
                    ),
                    confidence_source="domain_rule_template",
                    rule_scope="cross_table",
                    source_field_name=field_name,
                    target_table_name=target_table,
                    target_field_name=target_field,
                    notes="Generated from primary/foreign-key metadata.",
                )
            )
    return deduplicate_rules(rules)


def deduplicate_cross_field_rules(
    rules: list[CrossFieldQualityRule],
) -> list[CrossFieldQualityRule]:
    """Remove duplicate cross-field rules while keeping first evidence."""
    deduped: list[CrossFieldQualityRule] = []
    seen: set[tuple[str, str, str, tuple[str, ...], str, str]] = set()
    for rule in rules:
        key = (
            rule.source_table_name,
            rule.rule_scope,
            rule.rule_type,
            tuple(sorted(rule.field_group)),
            rule.target_table_name or "",
            rule.target_field_name or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)
    return deduped


def cross_field_rule_to_suggestion(
    rule: CrossFieldQualityRule,
) -> QualityRuleSuggestion:
    """Represent one cross-field rule in the shared review model."""
    primary_field = (
        rule.source_field_name
        or (rule.field_group[0] if rule.field_group else "__cross_field__")
    )
    return QualityRuleSuggestion(
        source_table_name=rule.source_table_name,
        source_field_name=primary_field,
        rule_name=rule.rule_name,
        rule_description=rule.rule_description,
        recommended_field_name=None,
        target_table_name=rule.target_table_name,
        target_field_name=rule.target_field_name,
        rule_type=rule.rule_type,
        rule_expression=rule.rule_expression,
        severity=rule.severity,
        priority=rule.priority,
        risk_level=rule.risk_level,
        confidence=rule.confidence,
        requires_manual_review=rule.requires_manual_review,
        review_priority=rule.review_priority,
        rule_scope=rule.rule_scope,
        field_group=list(rule.field_group),
        recommendation_source=rule.recommendation_source,
        match_basis=rule.match_basis,
        reason=rule.reason,
        export_formats=list(rule.export_formats),
        notes=rule.notes,
    )

"""Quality rule review replay and confirmed rule construction helpers."""

from collections import Counter
from datetime import datetime

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.review.quality_override_store import (
    build_quality_rule_key,
    build_quality_rule_override_lookup,
)
from app.core.rules.config_loader import get_quality_rule_policies_config

REVIEW_ACTIONS = {"accept", "reject", "edit", "mark_for_manual_review"}


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_action(value: object) -> str:
    action = str(value or "accept").strip()
    return action if action in REVIEW_ACTIONS else "accept"


def _priority_for_severity(severity: str | None, fallback: str | None = None) -> str | None:
    if not severity:
        return fallback
    policies = get_quality_rule_policies_config()
    priority_map = policies.get("severity_default_priority_map", {})
    if not isinstance(priority_map, dict):
        return fallback
    return priority_map.get(str(severity).lower(), fallback)


def _review_input_for(
    review_inputs: dict[str, dict[str, str | None]],
    suggestion: QualityRuleSuggestion,
) -> dict[str, str | None]:
    exact_key = build_quality_rule_key(
        suggestion.source_table_name,
        suggestion.source_field_name,
        suggestion.rule_type,
        rule_scope=suggestion.rule_scope,
        field_group=suggestion.field_group,
    )
    legacy_key = f"{suggestion.source_table_name}.{suggestion.source_field_name}.{suggestion.rule_type}"
    field_key = f"{suggestion.source_table_name}.{suggestion.source_field_name}"
    return (
        review_inputs.get(exact_key)
        or review_inputs.get(legacy_key)
        or review_inputs.get(field_key)
        or {}
    )


def build_quality_rule_review_records_from_results(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    review_inputs: dict[str, dict[str, str | None]] | None = None,
    source: str = "review_workbench",
) -> list[QualityRuleReviewRecord]:
    """Convert quality rule suggestions and user review inputs into records."""
    review_inputs = review_inputs or {}
    records: list[QualityRuleReviewRecord] = []

    for suggestion in quality_rule_suggestions:
        user_input = _review_input_for(review_inputs, suggestion)
        action = _normalize_action(user_input.get("review_action"))
        final_rule_expression = _normalize_optional_text(
            user_input.get("final_rule_expression")
        )
        final_severity = _normalize_optional_text(user_input.get("final_severity"))

        if action == "accept":
            final_rule_expression = suggestion.rule_expression
            final_severity = suggestion.severity
        elif action in {"reject", "mark_for_manual_review"}:
            final_rule_expression = final_rule_expression or suggestion.rule_expression
            final_severity = final_severity or suggestion.severity
        else:
            final_rule_expression = final_rule_expression or suggestion.rule_expression
            final_severity = final_severity or suggestion.severity

        records.append(
            QualityRuleReviewRecord(
                source_table_name=suggestion.source_table_name,
                source_field_name=suggestion.source_field_name,
                rule_scope=suggestion.rule_scope,
                field_group=list(suggestion.field_group),
                rule_type=suggestion.rule_type,
                original_rule_expression=suggestion.rule_expression,
                final_rule_expression=final_rule_expression,
                original_severity=suggestion.severity,
                final_severity=final_severity,
                review_action=action,
                confidence=suggestion.confidence,
                review_priority=suggestion.review_priority,
                reviewer_note=_normalize_optional_text(user_input.get("reviewer_note")),
                reviewed_at=_utc_now(),
                source=source,
            )
        )

    return records


def summarize_quality_rule_review_records(
    records: list[QualityRuleReviewRecord] | None = None,
    confirmed_count: int = 0,
) -> dict[str, object]:
    """Aggregate quality rule review actions into report-friendly counts."""
    counter: Counter[str] = Counter(record.review_action for record in records or [])
    priority_counter: Counter[str] = Counter(
        record.review_priority or "unspecified" for record in records or []
    )
    total_reviewed_count = sum(counter.values())
    cross_field_confirmed_count = sum(
        1
        for record in records or []
        if record.rule_scope == "cross_field"
        and record.review_action in {"accept", "edit"}
    )
    low_confidence_reviewed_count = sum(
        1
        for record in records or []
        if record.confidence is not None and record.confidence <= 0.4
    )
    return {
        "accepted_count": counter.get("accept", 0),
        "rejected_count": counter.get("reject", 0),
        "edited_count": counter.get("edit", 0),
        "manual_review_count": counter.get("mark_for_manual_review", 0),
        "total_reviewed_count": total_reviewed_count,
        "confirmed_count": confirmed_count,
        "cross_field_confirmed_count": cross_field_confirmed_count,
        "low_confidence_reviewed_count": low_confidence_reviewed_count,
        "review_priority_counts": dict(priority_counter),
    }


def apply_quality_rule_overrides_to_results(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    override_records: list[QualityRuleReviewRecord] | None = None,
) -> tuple[list[QualityRuleSuggestion], int, dict[str, object]]:
    """Apply saved quality rule review overrides to current suggestions."""
    override_lookup = build_quality_rule_override_lookup(override_records)
    reviewed_suggestions: list[QualityRuleSuggestion] = []
    applied_records: list[QualityRuleReviewRecord] = []

    for suggestion in quality_rule_suggestions:
        key = build_quality_rule_key(
            suggestion.source_table_name,
            suggestion.source_field_name,
            suggestion.rule_type,
            rule_scope=suggestion.rule_scope,
            field_group=suggestion.field_group,
        )
        override = override_lookup.get(key)
        if override is None:
            reviewed_suggestions.append(suggestion)
            continue

        applied_records.append(override)
        payload = suggestion.model_dump()
        action = _normalize_action(override.review_action)

        if action == "accept":
            payload["confirmed_source"] = "override_accept"
            payload["notes"] = (
                f"{suggestion.notes} Override accept applied."
                if suggestion.notes
                else "Override accept applied."
            )
        elif action == "edit":
            payload["rule_expression"] = (
                override.final_rule_expression or suggestion.rule_expression
            )
            payload["severity"] = override.final_severity or suggestion.severity
            payload["priority"] = _priority_for_severity(
                payload["severity"],
                suggestion.priority,
            )
            payload["confirmed_source"] = "override_edit"
            payload["notes"] = (
                f"{suggestion.notes} Override edit applied."
                if suggestion.notes
                else "Override edit applied."
            )
        elif action == "reject":
            payload["confirmed_source"] = "override_reject"
            payload["notes"] = (
                f"{suggestion.notes} Override reject applied."
                if suggestion.notes
                else "Override reject applied."
            )
        elif action == "mark_for_manual_review":
            payload["confirmed_source"] = "override_manual_review"
            payload["notes"] = (
                f"{suggestion.notes} Marked for manual review."
                if suggestion.notes
                else "Marked for manual review."
            )

        payload["review_action"] = action
        payload["reviewer_note"] = override.reviewer_note
        reviewed_suggestions.append(QualityRuleSuggestion(**payload))

    confirmed_rules = build_confirmed_quality_rules(
        quality_rule_suggestions,
        applied_records,
    )
    return (
        reviewed_suggestions,
        len(applied_records),
        summarize_quality_rule_review_records(applied_records, len(confirmed_rules)),
    )


def build_confirmed_quality_rules(
    quality_rule_suggestions: list[QualityRuleSuggestion],
    review_records: list[QualityRuleReviewRecord] | None = None,
) -> list[ConfirmedQualityRule]:
    """Build deduplicated confirmed quality rules from suggestions and review records."""
    review_lookup = build_quality_rule_override_lookup(review_records)
    confirmed_rules: list[ConfirmedQualityRule] = []
    seen: set[tuple[str, str, tuple[str, ...], str]] = set()

    for suggestion in quality_rule_suggestions:
        key = build_quality_rule_key(
            suggestion.source_table_name,
            suggestion.source_field_name,
            suggestion.rule_type,
            rule_scope=suggestion.rule_scope,
            field_group=suggestion.field_group,
        )
        review = review_lookup.get(key)
        if review is None:
            continue

        action = _normalize_action(review.review_action)
        if action in {"reject", "mark_for_manual_review"}:
            continue

        dedupe_key = (
            suggestion.source_table_name,
            suggestion.rule_scope,
            tuple(sorted(suggestion.field_group or [suggestion.source_field_name])),
            suggestion.rule_type,
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        if action == "edit":
            rule_expression = review.final_rule_expression or suggestion.rule_expression
            severity = review.final_severity or suggestion.severity
            confirmation_source = "override_edit"
        else:
            rule_expression = suggestion.rule_expression
            severity = suggestion.severity
            confirmation_source = "override_accept"

        confirmed_rules.append(
            ConfirmedQualityRule(
                source_table_name=suggestion.source_table_name,
                source_field_name=suggestion.source_field_name,
                recommended_field_name=suggestion.recommended_field_name,
                rule_type=suggestion.rule_type,
                rule_expression=rule_expression,
                severity=severity,
                priority=_priority_for_severity(severity, suggestion.priority),
                rule_scope=suggestion.rule_scope,
                field_group=list(suggestion.field_group),
                confidence=suggestion.confidence,
                review_priority=suggestion.review_priority,
                confirmation_source=confirmation_source,
                match_basis=suggestion.match_basis,
                reason=suggestion.reason,
                notes=review.reviewer_note or suggestion.notes,
            )
        )

    return confirmed_rules


# TODO: add manual-review queues, cross-field rules, and execution-runtime handoff when quality governance moves beyond local review replay.

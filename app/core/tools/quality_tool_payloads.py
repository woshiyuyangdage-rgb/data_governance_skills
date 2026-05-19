"""Payload coercion helpers for quality tool handlers."""

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.skills.quality_rule_recommendation import QualityRuleRecommendationSkill


def coerce_quality_rule_suggestions(
    payload: object,
) -> list[QualityRuleSuggestion]:
    """Coerce raw payload into quality rule suggestions."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("quality_rule_suggestions must be a list.")
    return [
        item
        if isinstance(item, QualityRuleSuggestion)
        else QualityRuleSuggestion.model_validate(item)
        for item in payload
    ]


def coerce_cross_field_quality_rules(
    payload: object,
) -> list[CrossFieldQualityRule]:
    """Coerce raw payload into cross-field quality rules."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("cross_field_quality_rules must be a list.")
    return [
        item
        if isinstance(item, CrossFieldQualityRule)
        else CrossFieldQualityRule.model_validate(item)
        for item in payload
    ]


def cross_field_rules_as_suggestions(
    rules: list[CrossFieldQualityRule],
) -> list[QualityRuleSuggestion]:
    """Convert cross-field rules to review-compatible quality suggestions."""
    return [
        QualityRuleRecommendationSkill.cross_field_rule_to_suggestion(rule)
        for rule in rules
    ]


def coerce_quality_review_records(
    payload: object,
) -> list[QualityRuleReviewRecord]:
    """Coerce raw payload into quality review records."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("records must be a list.")
    return [
        item
        if isinstance(item, QualityRuleReviewRecord)
        else QualityRuleReviewRecord.model_validate(item)
        for item in payload
    ]


def coerce_confirmed_quality_rules(
    payload: object,
) -> list[ConfirmedQualityRule]:
    """Coerce raw payload into confirmed quality rules."""
    if payload is None:
        return []
    if not isinstance(payload, list):
        raise ValueError("confirmed_quality_rules must be a list.")
    return [
        item
        if isinstance(item, ConfirmedQualityRule)
        else ConfirmedQualityRule.model_validate(item)
        for item in payload
    ]


def coerce_execution_ready_package(payload: object) -> ExecutionReadyPackage | None:
    """Coerce raw payload into an execution-ready package."""
    if payload is None:
        return None
    if isinstance(payload, ExecutionReadyPackage):
        return payload
    if isinstance(payload, dict):
        return ExecutionReadyPackage.model_validate(payload)
    raise ValueError("execution_ready_package must be an object.")

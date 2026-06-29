"""Compatibility wrapper for data quality rule skill modules."""

from app.core.skills.data_quality_rule_skill.quality_rule_cross_field import (
    BuildRule,
    DeduplicateRules,
    FieldTokens,
    FindField,
    TableTokens,
    build_cross_field_rule,
    cross_field_rule_to_suggestion,
    deduplicate_cross_field_rules,
    detect_cross_field_patterns,
    detect_cross_table_reference_rules,
    detect_domain_rule_candidates,
    find_field_by_tokens,
)

__all__ = [
    "BuildRule",
    "DeduplicateRules",
    "FieldTokens",
    "FindField",
    "TableTokens",
    "build_cross_field_rule",
    "cross_field_rule_to_suggestion",
    "deduplicate_cross_field_rules",
    "detect_cross_field_patterns",
    "detect_cross_table_reference_rules",
    "detect_domain_rule_candidates",
    "find_field_by_tokens",
]

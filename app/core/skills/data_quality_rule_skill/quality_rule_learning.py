"""Association-rule learning helpers for quality rule recommendations."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable

import pandas as pd

try:
    from mlxtend.frequent_patterns import association_rules, fpgrowth
except Exception:  # pragma: no cover - optional dependency fallback
    association_rules = None  # type: ignore[assignment]
    fpgrowth = None  # type: ignore[assignment]

from app.core.models.field_meta import FieldMeta
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.normalize import normalize_tokens, split_tokens
from app.core.review.quality_override_store import load_quality_rule_overrides
from app.core.rules.config_loader import get_quality_review_policies_config

ACCEPTED_REVIEW_ACTIONS = {"accept", "edit"}
RULE_ITEM_PREFIX = "rule:"
SOURCE_ITEM_PREFIX = "source:"
TYPE_ITEM_PREFIX = "type:"
TOKEN_ITEM_PREFIX = "token:"
FIELD_ITEM_PREFIX = "field:"
BASIS_ITEM_PREFIX = "basis:"


@dataclass(frozen=True)
class LearnedQualityRuleMatch:
    """One mined recommendation signal for a quality rule suggestion."""

    rule_type: str
    support: float
    confidence: float
    lift: float
    evidence_items: tuple[str, ...]


@dataclass(frozen=True)
class QualityRuleLearningHealth:
    """Health summary for quality-rule association learning."""

    enabled: bool = True
    dependency_available: bool = False
    accepted_record_count: int = 0
    min_records: int = 3
    association_rule_count: int = 0
    learned_rule_types: tuple[str, ...] = ()
    status: str = "dependency_unavailable"


def quality_rule_learning_policy() -> dict[str, object]:
    """Return association-rule learning configuration."""
    config = get_quality_review_policies_config()
    policy = config.get("association_rule_learning", {})
    return policy if isinstance(policy, dict) else {}


def association_rule_learning_enabled() -> bool:
    """Return whether historical quality-rule learning is enabled and available."""
    policy = quality_rule_learning_policy()
    return bool(policy.get("enabled", True)) and fpgrowth is not None and association_rules is not None


def _dependency_available() -> bool:
    return fpgrowth is not None and association_rules is not None


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _tokens_from_name(name: str | None) -> tuple[str, ...]:
    tokens = split_tokens(name or "")
    normalized_tokens = normalize_tokens(tokens)
    return tuple(dict.fromkeys(str(token).strip().lower() for token in normalized_tokens if str(token).strip()))


def _data_type_item(data_type: str | None) -> str | None:
    if not data_type:
        return None
    normalized_type = data_type.strip().lower().split("(", 1)[0]
    return f"{TYPE_ITEM_PREFIX}{normalized_type}" if normalized_type else None


def _field_context_items(
    *,
    field_name: str,
    data_type: str | None,
    recommended_field_name: str | None,
    recommendation_source: str | None,
    match_basis: str | None,
) -> tuple[str, ...]:
    items: list[str] = []
    data_type_token = _data_type_item(data_type)
    if data_type_token:
        items.append(data_type_token)

    for token in _tokens_from_name(field_name):
        items.append(f"{TOKEN_ITEM_PREFIX}{token}")

    for token in _tokens_from_name(recommended_field_name):
        items.append(f"{FIELD_ITEM_PREFIX}{token}")

    if recommendation_source:
        items.append(f"{SOURCE_ITEM_PREFIX}{str(recommendation_source).strip().lower()}")

    if match_basis:
        basis_text = str(match_basis).strip().lower()
        if "standard_code=" in basis_text:
            items.append(f"{BASIS_ITEM_PREFIX}{basis_text.split('standard_code=', 1)[1]}")

    return tuple(dict.fromkeys(items))


def _record_items(record: QualityRuleReviewRecord) -> tuple[str, ...]:
    context_items = tuple(record.learning_context) or _field_context_items(
        field_name=record.source_field_name,
        data_type=None,
        recommended_field_name=record.recommended_field_name,
        recommendation_source=record.recommendation_source,
        match_basis=record.match_basis,
    )
    return tuple([*context_items, f"{RULE_ITEM_PREFIX}{record.rule_type.strip().lower()}"])


def _accepted_learning_records(
    records: list[QualityRuleReviewRecord],
) -> list[QualityRuleReviewRecord]:
    return [
        record
        for record in records
        if str(record.review_action).strip() in ACCEPTED_REVIEW_ACTIONS
        and str(record.rule_type).strip()
    ]


def summarize_quality_rule_learning(
    records: list[QualityRuleReviewRecord] | None = None,
    associations: Iterable[dict[str, object]] | None = None,
) -> QualityRuleLearningHealth:
    """Return a maintenance-friendly summary for quality-rule learning."""
    policy = quality_rule_learning_policy()
    enabled = bool(policy.get("enabled", True))
    dependency_available = _dependency_available()
    min_records = _safe_int(policy.get("min_records", 3), 3)
    review_records = records if records is not None else load_quality_rule_overrides()
    accepted_records = _accepted_learning_records(review_records)

    if associations is not None:
        association_payload = tuple(associations)
    elif enabled and dependency_available and len(accepted_records) >= min_records:
        association_payload = (
            tuple(mine_quality_rule_associations(review_records))
            if records is not None
            else load_quality_rule_associations()
        )
    else:
        association_payload = ()

    learned_rule_types = tuple(
        sorted(
            {
                str(rule.get("rule_type") or "").strip()
                for rule in association_payload
                if str(rule.get("rule_type") or "").strip()
            }
        )
    )
    if not enabled:
        status = "disabled"
    elif not dependency_available:
        status = "dependency_unavailable"
    elif len(accepted_records) < min_records:
        status = "insufficient_records"
    elif not association_payload:
        status = "no_associations"
    else:
        status = "active"

    return QualityRuleLearningHealth(
        enabled=enabled,
        dependency_available=dependency_available,
        accepted_record_count=len(accepted_records),
        min_records=min_records,
        association_rule_count=len(association_payload),
        learned_rule_types=learned_rule_types,
        status=status,
    )


def _one_hot_transactions(transactions: list[tuple[str, ...]]) -> pd.DataFrame:
    item_universe = sorted({item for transaction in transactions for item in transaction})
    rows = [
        {item: item in transaction for item in item_universe}
        for transaction in transactions
    ]
    return pd.DataFrame(rows, columns=item_universe, dtype=bool)


def mine_quality_rule_associations(
    records: list[QualityRuleReviewRecord] | None = None,
) -> list[dict[str, object]]:
    """Mine accepted quality-rule review records into association rules."""
    if not association_rule_learning_enabled():
        return []

    policy = quality_rule_learning_policy()
    min_records = _safe_int(policy.get("min_records", 3), 3)
    min_support = _safe_float(policy.get("min_support", 0.2), 0.2)
    min_confidence = _safe_float(policy.get("min_confidence", 0.8), 0.8)

    records = records if records is not None else load_quality_rule_overrides()
    accepted_records = _accepted_learning_records(records)
    if len(accepted_records) < min_records:
        return []

    transactions = [_record_items(record) for record in accepted_records]
    transactions = [transaction for transaction in transactions if len(transaction) >= 2]
    if len(transactions) < min_records:
        return []

    transaction_frame = _one_hot_transactions(transactions)
    frequent_itemsets = fpgrowth(
        transaction_frame,
        min_support=min_support,
        use_colnames=True,
    )
    if frequent_itemsets.empty:
        return []

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            message="invalid value encountered in divide",
        )
        rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=min_confidence,
        )
    if rules.empty:
        return []

    mined_rules: list[dict[str, object]] = []
    for row in rules.to_dict("records"):
        consequents = tuple(sorted(str(item) for item in row["consequents"]))
        rule_consequents = [
            item for item in consequents if item.startswith(RULE_ITEM_PREFIX)
        ]
        if len(rule_consequents) != 1:
            continue
        antecedents = tuple(
            sorted(str(item) for item in row["antecedents"] if not str(item).startswith(RULE_ITEM_PREFIX))
        )
        if not antecedents:
            continue
        mined_rules.append(
            {
                "antecedents": antecedents,
                "rule_type": rule_consequents[0].removeprefix(RULE_ITEM_PREFIX),
                "support": float(row["support"]),
                "confidence": float(row["confidence"]),
                "lift": float(row.get("lift", 0.0)),
            }
        )
    return mined_rules


@lru_cache(maxsize=1)
def load_quality_rule_associations() -> tuple[dict[str, object], ...]:
    """Load and cache mined quality-rule association rules."""
    return tuple(mine_quality_rule_associations())


def clear_quality_rule_learning_caches() -> None:
    """Clear mined association-rule cache."""
    load_quality_rule_associations.cache_clear()


def _field_context_for_suggestion(
    suggestion: QualityRuleSuggestion,
    field_lookup: dict[str, FieldMeta],
) -> tuple[str, ...]:
    if suggestion.learning_context:
        return tuple(suggestion.learning_context)
    field = field_lookup.get(
        f"{suggestion.source_table_name}.{suggestion.source_field_name}"
    )
    return _field_context_items(
        field_name=suggestion.source_field_name,
        data_type=field.data_type if field is not None else None,
        recommended_field_name=suggestion.recommended_field_name,
        recommendation_source=suggestion.recommendation_source,
        match_basis=suggestion.match_basis,
    )


def _build_field_lookup(fields: Iterable[tuple[str, FieldMeta]]) -> dict[str, FieldMeta]:
    return {f"{table_name}.{field.field_name}": field for table_name, field in fields}


def learned_match_for_suggestion(
    suggestion: QualityRuleSuggestion,
    field_lookup: dict[str, FieldMeta],
    association_rules_payload: tuple[dict[str, object], ...] | None = None,
) -> LearnedQualityRuleMatch | None:
    """Return the strongest mined association matching one quality suggestion."""
    if not association_rule_learning_enabled():
        return None
    rules_payload = association_rules_payload
    if rules_payload is None:
        rules_payload = load_quality_rule_associations()
    if not rules_payload:
        return None

    context_items = set(_field_context_for_suggestion(suggestion, field_lookup))
    matches: list[LearnedQualityRuleMatch] = []
    for rule in rules_payload:
        if str(rule.get("rule_type", "")).strip() != suggestion.rule_type:
            continue
        antecedents = tuple(str(item) for item in rule.get("antecedents", ()))
        if not antecedents or not set(antecedents).issubset(context_items):
            continue
        matches.append(
            LearnedQualityRuleMatch(
                rule_type=suggestion.rule_type,
                support=float(rule.get("support", 0.0)),
                confidence=float(rule.get("confidence", 0.0)),
                lift=float(rule.get("lift", 0.0)),
                evidence_items=antecedents,
            )
        )

    if not matches:
        return None
    return max(
        matches,
        key=lambda item: (
            item.confidence,
            item.support,
            len(item.evidence_items),
            item.lift,
        ),
    )


def apply_learned_quality_rule_priority(
    suggestions: list[QualityRuleSuggestion],
    fields: Iterable[tuple[str, FieldMeta]],
) -> list[QualityRuleSuggestion]:
    """Promote suggestions whose rule type matches mined human-review patterns."""
    if not suggestions or not association_rule_learning_enabled():
        return suggestions

    policy = quality_rule_learning_policy()
    boost_priority = str(policy.get("boost_review_priority", "learned_review_priority"))
    rules_payload = load_quality_rule_associations()
    if not rules_payload:
        return suggestions

    field_lookup = _build_field_lookup(fields)
    ranked: list[QualityRuleSuggestion] = []
    for suggestion in suggestions:
        learned_match = learned_match_for_suggestion(
            suggestion,
            field_lookup,
            rules_payload,
        )
        if learned_match is None:
            ranked.append(suggestion)
            continue

        payload = suggestion.model_dump()
        payload["learned_support"] = round(learned_match.support, 4)
        payload["learned_confidence"] = round(learned_match.confidence, 4)
        payload["review_priority"] = boost_priority
        evidence = (
            "learned_from_quality_review_history="
            f"confidence:{learned_match.confidence:.2f},"
            f"support:{learned_match.support:.2f},"
            f"items:{list(learned_match.evidence_items)}"
        )
        payload["notes"] = (
            f"{suggestion.notes} {evidence}" if suggestion.notes else evidence
        )
        ranked.append(QualityRuleSuggestion(**payload))

    return sorted(
        ranked,
        key=lambda item: (
            item.learned_confidence or 0.0,
            item.learned_support or 0.0,
            item.confidence or 0.0,
        ),
        reverse=True,
    )

"""Rule-based P2 skill for quality rule recommendations."""

from collections import defaultdict

from pydantic import BaseModel, Field

from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.normalize import clean_text, expand_tokens_with_evidence, normalize_tokens, split_tokens
from app.core.rules.config_loader import (
    get_issue_severity,
    get_quality_rule_policies_config,
    get_quality_review_policies_config,
    get_quality_rule_templates_config,
)
from app.core.skills.base_skill import BaseSkill
from app.core.skills.quality_rule_cross_field import (
    build_cross_field_rule,
    cross_field_rule_to_suggestion,
    deduplicate_cross_field_rules,
    detect_cross_field_patterns,
    detect_domain_rule_candidates,
    find_field_by_tokens,
)


class QualityRuleRecommendationInput(BaseModel):
    """Input schema for quality rule recommendation."""

    tables: list[TableMeta] = Field(default_factory=list)
    confirmed_mapping_results: list[MappingResult] = Field(default_factory=list)
    mapping_results: list[MappingResult] = Field(default_factory=list)
    confirmed_stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    stg_suggestions: list[StgFieldSuggestion] = Field(default_factory=list)
    domain_pack_hints: dict = Field(default_factory=dict)


class QualityRuleRecommendationOutput(BaseModel):
    """Output schema for quality rule recommendation."""

    quality_rule_suggestions: list[QualityRuleSuggestion] = Field(default_factory=list)
    cross_field_quality_rules: list[CrossFieldQualityRule] = Field(default_factory=list)
    quality_rule_packages: list[QualityRulePackage] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


class QualityRuleRecommendationSkill(BaseSkill):
    """Recommend explainable field-level quality rules from governance context."""

    skill_name = "quality_rule_recommendation"
    version = "0.6.0"
    description = "P3.5 rule-based quality intelligence using field, domain, and cross-field metadata patterns."

    @staticmethod
    def build_template_lookup() -> dict[str, list[dict[str, str]]]:
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

    @staticmethod
    def _priority_for_severity(severity: str) -> str | None:
        policies = get_quality_rule_policies_config()
        priority_map = policies.get("severity_default_priority_map", {})
        return priority_map.get(severity.lower())

    @staticmethod
    def _confidence_policy() -> dict[str, float]:
        policies = get_quality_review_policies_config()
        confidence_policy = policies.get("confidence_policy", {})
        if not isinstance(confidence_policy, dict):
            return {}
        return {
            str(key): float(value)
            for key, value in confidence_policy.items()
            if isinstance(value, (int, float))
        }

    @classmethod
    def compute_quality_rule_confidence(cls, match_source: str) -> float:
        """Return deterministic confidence for the recommendation evidence type."""
        policy = cls._confidence_policy()
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

    @classmethod
    def infer_review_priority(
        cls,
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
        if str(rule_scope) == "cross_field" and bool(
            priority_policy.get("prioritize_cross_field_rules", True)
        ):
            if confidence is not None and confidence < medium_threshold:
                return "high_review_priority"
            return "medium_review_priority"
        if confidence is not None and confidence < medium_threshold:
            return "high_review_priority"
        return "standard_review_priority"

    @staticmethod
    def _field_key(table_name: str, field_name: str) -> str:
        return f"{table_name}.{field_name}"

    @staticmethod
    def _tokenize_name(name: str | None) -> tuple[list[str], list[str]]:
        cleaned = clean_text(name or "", lower=False)
        tokens = split_tokens(cleaned)
        expanded_tokens, _, _ = expand_tokens_with_evidence(tokens)
        normalized_token_list = normalize_tokens(expanded_tokens)
        return tokens, normalized_token_list

    @staticmethod
    def _field_tokens(field_name: str) -> set[str]:
        _, normalized_tokens = QualityRuleRecommendationSkill._tokenize_name(field_name)
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

    @classmethod
    def _table_tokens(cls, table: TableMeta) -> set[str]:
        tokens: set[str] = set()
        for value in [table.table_name, table.table_description, table.table_name_cn]:
            _, normalized_tokens = cls._tokenize_name(value)
            tokens.update(str(token).lower() for token in normalized_tokens)
        for field in table.fields:
            tokens.update(cls._field_tokens(field.field_name))
        return tokens

    @classmethod
    def _mapping_lookup(
        cls,
        results: list[MappingResult],
    ) -> dict[str, MappingResult]:
        return {cls._field_key(item.table_name, item.field_name): item for item in results}

    @classmethod
    def _stg_lookup(
        cls,
        suggestions: list[StgFieldSuggestion],
    ) -> dict[str, StgFieldSuggestion]:
        return {
            cls._field_key(item.source_table_name, item.source_field_name): item
            for item in suggestions
        }

    @staticmethod
    def _candidate_templates_from_standard_code(standard_code: str | None) -> list[str]:
        if not standard_code:
            return []
        policies = get_quality_rule_policies_config()
        mapping = policies.get("standard_code_to_template_map", {})
        matched = mapping.get(standard_code.strip().lower())
        return [str(matched).strip().lower()] if matched else []

    @staticmethod
    def _candidate_templates_from_tokens(tokens: list[str]) -> list[str]:
        policies = get_quality_rule_policies_config()
        token_map = policies.get("token_to_template_map", {})
        matched: list[str] = []
        for token in tokens:
            template_name = token_map.get(token.strip().lower())
            if template_name:
                matched.append(str(template_name).strip().lower())
        return list(dict.fromkeys(matched))

    @staticmethod
    def _candidate_templates_from_data_type(data_type: str | None) -> list[str]:
        if not data_type:
            return []
        policies = get_quality_rule_policies_config()
        normalized_type = data_type.strip().lower().split("(", 1)[0]
        mapping = policies.get("data_type_default_rules", {})
        candidates = mapping.get(normalized_type, [])
        if not isinstance(candidates, list):
            return []
        return [str(item).strip().lower() for item in candidates if str(item).strip()]

    @classmethod
    def infer_rule_templates_from_mapping(
        cls,
        mapping_result: MappingResult | None,
    ) -> tuple[list[str], str | None, str | None]:
        """Infer templates from a mapping result."""
        if mapping_result is None:
            return [], None, None
        templates = cls._candidate_templates_from_standard_code(
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

    @classmethod
    def infer_rule_templates_from_stg_name(
        cls,
        stg_suggestion: StgFieldSuggestion | None,
        recommendation_source: str,
    ) -> tuple[list[str], str | None, str | None]:
        """Infer templates from an STG field suggestion name."""
        if stg_suggestion is None:
            return [], None, None
        _, normalized_tokens = cls._tokenize_name(stg_suggestion.recommended_stg_field_name)
        templates = cls._candidate_templates_from_tokens(normalized_tokens)
        if not templates:
            templates = cls._candidate_templates_from_data_type(
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

    @classmethod
    def infer_rule_templates_from_source_name(
        cls,
        field_name: str,
        data_type: str | None,
    ) -> tuple[list[str], str | None, str | None]:
        """Infer templates from source-field tokens and type."""
        _, normalized_tokens = cls._tokenize_name(field_name)
        templates = cls._candidate_templates_from_tokens(normalized_tokens)
        basis = None
        reason = None
        if templates:
            basis = f"source_field_name={field_name}"
            reason = f"Matched template from source field name {field_name}"
            return templates, basis, reason

        templates = cls._candidate_templates_from_data_type(data_type)
        if templates:
            basis = f"source_data_type={data_type}"
            reason = f"Matched fallback data-type template from source_data_type={data_type}"
        return templates, basis, reason

    @classmethod
    def build_quality_rule_suggestion(
        cls,
        source_table_name: str,
        source_field_name: str,
        recommended_field_name: str | None,
        recommendation_source: str,
        template_name: str,
        rule_template: dict[str, str],
        match_basis: str | None,
        reason: str | None,
    ) -> QualityRuleSuggestion:
        """Create one normalized quality-rule suggestion."""
        severity = str(rule_template.get("severity", "low")).lower()
        confidence = cls.compute_quality_rule_confidence(recommendation_source)
        return QualityRuleSuggestion(
            source_table_name=source_table_name,
            source_field_name=source_field_name,
            recommended_field_name=recommended_field_name,
            rule_type=str(rule_template.get("rule_type", "")),
            rule_expression=rule_template.get("rule_expression"),
            severity=severity,
            priority=cls._priority_for_severity(severity),
            confidence=confidence,
            review_priority=cls.infer_review_priority(
                rule_scope="field",
                rule_type=str(rule_template.get("rule_type", "")),
                confidence=confidence,
            ),
            rule_scope="field",
            field_group=[source_field_name],
            recommendation_source=recommendation_source,
            match_basis=match_basis,
            reason=reason,
            notes=f"Recommended from template={template_name}.",
        )

    @staticmethod
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

    @classmethod
    def _build_cross_field_rule(
        cls,
        table_name: str,
        field_group: list[str],
        rule_type: str,
        rule_expression: str,
        severity: str,
        recommendation_source: str,
        match_basis: str,
        reason: str,
        confidence_source: str,
        notes: str | None = None,
    ) -> CrossFieldQualityRule:
        return build_cross_field_rule(
            table_name=table_name,
            field_group=field_group,
            rule_type=rule_type,
            rule_expression=rule_expression,
            severity=severity,
            priority_for_severity=cls._priority_for_severity,
            compute_quality_rule_confidence=cls.compute_quality_rule_confidence,
            infer_review_priority=cls.infer_review_priority,
            recommendation_source=recommendation_source,
            match_basis=match_basis,
            reason=reason,
            confidence_source=confidence_source,
            notes=notes,
        )

    @staticmethod
    def _find_field_by_tokens(
        field_tokens: dict[str, set[str]],
        required_tokens: set[str],
    ) -> str | None:
        return find_field_by_tokens(field_tokens, required_tokens)

    @classmethod
    def detect_cross_field_patterns(cls, table: TableMeta) -> list[CrossFieldQualityRule]:
        """Detect configured and built-in cross-field rules in one source table."""
        return detect_cross_field_patterns(
            table=table,
            field_tokens_for_name=cls._field_tokens,
            find_field=cls._find_field_by_tokens,
            build_rule=cls._build_cross_field_rule,
            deduplicate_rules=cls.deduplicate_cross_field_rules,
        )

    @classmethod
    def detect_domain_rule_candidates(cls, table: TableMeta) -> list[CrossFieldQualityRule]:
        """Detect domain-aware single-table rule candidates from configured templates."""
        return detect_domain_rule_candidates(
            table=table,
            table_tokens_for_table=cls._table_tokens,
            field_tokens_for_name=cls._field_tokens,
            find_field=cls._find_field_by_tokens,
            build_rule=cls._build_cross_field_rule,
            deduplicate_rules=cls.deduplicate_cross_field_rules,
        )

    @staticmethod
    def deduplicate_cross_field_rules(
        rules: list[CrossFieldQualityRule],
    ) -> list[CrossFieldQualityRule]:
        """Remove duplicate cross-field rules while keeping first evidence."""
        return deduplicate_cross_field_rules(rules)

    @staticmethod
    def cross_field_rule_to_suggestion(rule: CrossFieldQualityRule) -> QualityRuleSuggestion:
        """Represent one cross-field rule in the shared review model."""
        return cross_field_rule_to_suggestion(rule)

    @staticmethod
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

    def _select_basis_for_field(
        self,
        table_name: str,
        field_name: str,
        data_type: str | None,
        effective_mappings: dict[str, MappingResult],
        fallback_mappings: dict[str, MappingResult],
        effective_stg: dict[str, StgFieldSuggestion],
        fallback_stg: dict[str, StgFieldSuggestion],
    ) -> tuple[list[str], str, str | None, str | None, str | None]:
        lookup_key = self._field_key(table_name, field_name)

        mapping_result = effective_mappings.get(lookup_key)
        templates, match_basis, reason = self.infer_rule_templates_from_mapping(mapping_result)
        if templates:
            recommended_field_name = (
                mapping_result.recommended_standard_name
                or mapping_result.recommended_standard_code
            )
            return templates, "confirmed_mapping", recommended_field_name, match_basis, reason

        mapping_result = fallback_mappings.get(lookup_key)
        templates, match_basis, reason = self.infer_rule_templates_from_mapping(mapping_result)
        if templates:
            recommended_field_name = (
                mapping_result.recommended_standard_name
                or mapping_result.recommended_standard_code
            )
            return templates, "standard_mapping", recommended_field_name, match_basis, reason

        stg_suggestion = effective_stg.get(lookup_key)
        templates, match_basis, reason = self.infer_rule_templates_from_stg_name(
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
        templates, match_basis, reason = self.infer_rule_templates_from_stg_name(
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

        templates, match_basis, reason = self.infer_rule_templates_from_source_name(
            field_name,
            data_type,
        )
        return templates, "source_field_fallback", field_name, match_basis, reason

    def run(self, payload: QualityRuleRecommendationInput) -> QualityRuleRecommendationOutput:
        """Generate field-level quality rule suggestions from governance context."""
        if not payload.tables:
            return QualityRuleRecommendationOutput(
                quality_rule_suggestions=[],
                quality_rule_packages=[],
                issues=[],
                summary="No tables were provided, so quality rule recommendation was skipped.",
            )

        template_lookup = self.build_template_lookup()
        confirmed_mapping_lookup = self._mapping_lookup(payload.confirmed_mapping_results)
        mapping_lookup = self._mapping_lookup(payload.mapping_results)
        confirmed_stg_lookup = self._stg_lookup(payload.confirmed_stg_suggestions)
        stg_lookup = self._stg_lookup(payload.stg_suggestions)

        suggestions: list[QualityRuleSuggestion] = []
        cross_field_rules: list[CrossFieldQualityRule] = []
        issues: list[Issue] = []
        source_counter: dict[str, int] = defaultdict(int)
        table_buckets: dict[str, list[QualityRuleSuggestion]] = defaultdict(list)

        for table in payload.tables:
            for field in table.fields:
                (
                    template_names,
                    recommendation_source,
                    recommended_field_name,
                    match_basis,
                    reason,
                ) = self._select_basis_for_field(
                    table_name=table.table_name,
                    field_name=field.field_name,
                    data_type=field.data_type,
                    effective_mappings=confirmed_mapping_lookup,
                    fallback_mappings=mapping_lookup,
                    effective_stg=confirmed_stg_lookup,
                    fallback_stg=stg_lookup,
                )

                field_suggestions: list[QualityRuleSuggestion] = []
                for template_name in template_names:
                    for rule_template in template_lookup.get(template_name, []):
                        field_suggestions.append(
                            self.build_quality_rule_suggestion(
                                source_table_name=table.table_name,
                                source_field_name=field.field_name,
                                recommended_field_name=recommended_field_name,
                                recommendation_source=recommendation_source,
                                template_name=template_name,
                                rule_template=rule_template,
                                match_basis=match_basis,
                                reason=reason,
                            )
                        )

                deduped_field_suggestions = self.deduplicate_rules_for_field(field_suggestions)
                if not deduped_field_suggestions:
                    issues.append(
                        self.build_quality_issue(
                            issue_id=(
                                f"{self.skill_name}-missing-{table.table_name}-{field.field_name}"
                            ).replace(" ", "_"),
                            table_name=table.table_name,
                            field_name=field.field_name,
                            issue_type="quality_rule_not_recommended",
                            evidence=[
                                f"source_field_name={field.field_name}",
                                f"source_data_type={field.data_type}",
                                "no configured template matched the available governance context",
                            ],
                            suggestion=(
                                "Review whether this field needs a domain-specific quality rule "
                                "or whether the quality-rule templates should be extended."
                            ),
                            confidence=0.75,
                        )
                    )
                    continue

                if recommendation_source == "source_field_fallback":
                    issues.append(
                        self.build_quality_issue(
                            issue_id=(
                                f"{self.skill_name}-low-confidence-{table.table_name}-{field.field_name}"
                            ).replace(" ", "_"),
                            table_name=table.table_name,
                            field_name=field.field_name,
                            issue_type="quality_rule_low_confidence",
                            evidence=[
                                f"source_field_name={field.field_name}",
                                f"source_data_type={field.data_type}",
                                f"match_basis={match_basis}",
                            ],
                            suggestion=(
                                "Review this quality-rule recommendation because it was derived "
                                "from source metadata fallback instead of confirmed mapping or STG context."
                            ),
                            confidence=0.68,
                        )
                    )

                suggestions.extend(deduped_field_suggestions)
                table_buckets[table.table_name].extend(deduped_field_suggestions)
                source_counter[recommendation_source] += 1

            table_cross_field_rules = self.deduplicate_cross_field_rules(
                self.detect_cross_field_patterns(table)
                + self.detect_domain_rule_candidates(table)
            )
            cross_field_rules.extend(table_cross_field_rules)
            if table_cross_field_rules:
                source_counter["cross_field_domain_intelligence"] += len(
                    table_cross_field_rules
                )

        packages = [
            QualityRulePackage(
                source_table_name=table_name,
                field_rule_count=len(table_rules),
                quality_rules=table_rules,
                summary=(
                    f"Recommended {len(table_rules)} field-level quality rules for "
                    f"source table {table_name}."
                ),
            )
            for table_name, table_rules in sorted(table_buckets.items())
        ]

        field_rule_count = len(suggestions)
        cross_field_rule_count = len(cross_field_rules)
        low_confidence_count = sum(
            1
            for rule in list(suggestions)
            + [self.cross_field_rule_to_suggestion(rule) for rule in cross_field_rules]
            if rule.confidence is not None and rule.confidence <= 0.4
        )
        summary_parts = [
            f"Generated {field_rule_count} field-level quality rule suggestions",
            f"and {cross_field_rule_count} cross-field/domain-aware quality rules",
            f"across {len(packages)} source tables",
            f"and flagged {len(issues)} review issues.",
        ]
        if low_confidence_count:
            summary_parts.append(
                f"{low_confidence_count} rules were marked as low-confidence review priorities."
            )
        if source_counter:
            ordered_sources = ", ".join(
                f"{source}={count}" for source, count in sorted(source_counter.items())
            )
            summary_parts.append(f"Recommendation sources: {ordered_sources}.")

        return QualityRuleRecommendationOutput(
            quality_rule_suggestions=suggestions,
            cross_field_quality_rules=cross_field_rules,
            quality_rule_packages=packages,
            issues=issues,
            summary=" ".join(summary_parts),
        )

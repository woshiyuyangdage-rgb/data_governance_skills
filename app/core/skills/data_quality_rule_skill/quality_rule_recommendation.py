"""Rule-based P2 skill for quality rule recommendations."""

from collections import defaultdict

from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.issue import Issue
from app.core.models.mapping_result import MappingResult
from app.core.models.quality_rule_package import QualityRulePackage
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.stg_field_suggestion import StgFieldSuggestion
from app.core.models.table_meta import TableMeta
from app.core.skills.base_skill import BaseSkill
from app.core.skills.data_quality_rule_skill.quality_rule_cross_field import (
    build_cross_field_rule,
    cross_field_rule_to_suggestion,
    deduplicate_cross_field_rules,
    detect_cross_field_patterns,
    detect_cross_table_reference_rules,
    detect_domain_rule_candidates,
    find_field_by_tokens,
)
from app.core.skills.data_quality_rule_skill.quality_rule_field_rules import (
    build_quality_issue,
    build_quality_rule_suggestion,
    build_template_lookup,
    candidate_templates_from_data_type,
    candidate_templates_from_standard_code,
    candidate_templates_from_tokens,
    compute_quality_rule_confidence,
    confidence_policy,
    deduplicate_rules_for_field,
    field_key,
    field_tokens,
    infer_review_priority,
    infer_rule_templates_from_mapping,
    infer_rule_templates_from_source_name,
    infer_rule_templates_from_stg_name,
    mapping_lookup,
    priority_for_severity,
    select_basis_for_field,
    stg_lookup,
    table_tokens,
    tokenize_name,
)
from app.core.skills.data_quality_rule_skill.quality_rule_io import (
    QualityRuleRecommendationInput,
    QualityRuleRecommendationOutput,
)
from app.core.skills.data_quality_rule_skill.quality_rule_learning import (
    apply_learned_quality_rule_priority,
)


class QualityRuleRecommendationSkill(BaseSkill):
    """Recommend explainable field-level quality rules from governance context."""

    skill_name = "quality_rule_recommendation"
    version = "0.6.0"
    description = "P3.5 rule-based quality intelligence using field, domain, and cross-field metadata patterns."

    build_template_lookup = staticmethod(build_template_lookup)
    _priority_for_severity = staticmethod(priority_for_severity)
    _confidence_policy = staticmethod(confidence_policy)
    compute_quality_rule_confidence = staticmethod(compute_quality_rule_confidence)
    infer_review_priority = staticmethod(infer_review_priority)
    _field_key = staticmethod(field_key)
    _tokenize_name = staticmethod(tokenize_name)
    _field_tokens = staticmethod(field_tokens)
    _table_tokens = staticmethod(table_tokens)
    _mapping_lookup = staticmethod(mapping_lookup)
    _stg_lookup = staticmethod(stg_lookup)
    _candidate_templates_from_standard_code = staticmethod(
        candidate_templates_from_standard_code
    )
    _candidate_templates_from_tokens = staticmethod(candidate_templates_from_tokens)
    _candidate_templates_from_data_type = staticmethod(candidate_templates_from_data_type)
    infer_rule_templates_from_mapping = staticmethod(infer_rule_templates_from_mapping)
    infer_rule_templates_from_stg_name = staticmethod(infer_rule_templates_from_stg_name)
    infer_rule_templates_from_source_name = staticmethod(
        infer_rule_templates_from_source_name
    )
    build_quality_rule_suggestion = staticmethod(build_quality_rule_suggestion)
    deduplicate_rules_for_field = staticmethod(deduplicate_rules_for_field)
    build_quality_issue = staticmethod(build_quality_issue)

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
        rule_scope: str = "cross_field",
        source_field_name: str | None = None,
        target_table_name: str | None = None,
        target_field_name: str | None = None,
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
            rule_scope=rule_scope,
            source_field_name=source_field_name,
            target_table_name=target_table_name,
            target_field_name=target_field_name,
            recommendation_source=recommendation_source,
            match_basis=match_basis,
            reason=reason,
            confidence_source=confidence_source,
            notes=notes,
        )

    _find_field_by_tokens = staticmethod(find_field_by_tokens)

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

    deduplicate_cross_field_rules = staticmethod(deduplicate_cross_field_rules)
    cross_field_rule_to_suggestion = staticmethod(cross_field_rule_to_suggestion)

    @classmethod
    def detect_cross_table_reference_rules(
        cls,
        tables: list[TableMeta],
    ) -> list[CrossFieldQualityRule]:
        """Detect cross-table referential consistency candidates."""
        return detect_cross_table_reference_rules(
            tables=tables,
            build_rule=cls._build_cross_field_rule,
            deduplicate_rules=cls.deduplicate_cross_field_rules,
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
        return select_basis_for_field(
            table_name=table_name,
            field_name=field_name,
            data_type=data_type,
            effective_mappings=effective_mappings,
            fallback_mappings=fallback_mappings,
            effective_stg=effective_stg,
            fallback_stg=fallback_stg,
        )

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
                                source_data_type=field.data_type,
                                recommended_field_name=recommended_field_name,
                                recommendation_source=recommendation_source,
                                template_name=template_name,
                                rule_template=rule_template,
                                match_basis=match_basis,
                                reason=reason,
                                source_sample_values=field.sample_values,
                            )
                        )

                deduped_field_suggestions = self.deduplicate_rules_for_field(
                    field_suggestions
                )
                deduped_field_suggestions = apply_learned_quality_rule_priority(
                    deduped_field_suggestions,
                    [(table.table_name, field)],
                )
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

        cross_table_rules = self.detect_cross_table_reference_rules(payload.tables)
        if cross_table_rules:
            cross_field_rules.extend(cross_table_rules)
            source_counter["cross_table_reference_intelligence"] += len(
                cross_table_rules
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
        cross_field_rule_count = sum(
            1 for rule in cross_field_rules if rule.rule_scope == "cross_field"
        )
        cross_table_rule_count = sum(
            1 for rule in cross_field_rules if rule.rule_scope == "cross_table"
        )
        low_confidence_count = sum(
            1
            for rule in list(suggestions)
            + [self.cross_field_rule_to_suggestion(rule) for rule in cross_field_rules]
            if rule.confidence is not None and rule.confidence <= 0.4
        )
        summary_parts = [
            f"Generated {field_rule_count} field-level quality rule suggestions",
            f"{cross_field_rule_count} cross-field/domain-aware quality rules",
            f"and {cross_table_rule_count} cross-table reference rules",
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

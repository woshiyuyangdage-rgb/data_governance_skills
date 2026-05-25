"""Rule-based Text-to-SQL metadata readiness assessment."""

from __future__ import annotations

from collections import Counter

from app.core.models.field_meta import FieldMeta
from app.core.models.text_to_sql_readiness import (
    TextToSqlReadinessAssessmentResult,
    TextToSqlReadinessIssue,
    TextToSqlReadinessScore,
    TextToSqlTableMetadata,
)

DIMENSIONS = [
    "table_identifiability",
    "field_understandability",
    "relationship_inferability",
    "metric_clarity",
    "enum_explainability",
    "security_permission_fit",
    "query_example_support",
]
AMBIGUOUS_FIELD_TOKENS = {
    "status",
    "stat",
    "type",
    "typ",
    "flag",
    "flg",
    "amt",
    "amount",
    "code",
    "cd",
    "level",
    "lvl",
    "date",
    "dt",
}
TECHNICAL_TABLE_TOKENS = {"tmp", "temp", "bak", "backup", "test", "old", "his", "log"}
SENSITIVE_FIELD_TOKENS = {
    "id_no",
    "idcard",
    "id_card",
    "phone",
    "mobile",
    "email",
    "address",
    "acct",
    "account",
    "card",
    "secret",
}
ENUM_FIELD_TOKENS = {"status", "stat", "type", "typ", "flag", "flg", "code", "cd", "yn"}


def _text(value: object) -> str:
    return str(value or "").strip()


def _lower(value: object) -> str:
    return _text(value).lower()


def _tokenized_name(value: str | None) -> list[str]:
    text = _lower(value).replace("-", "_").replace(" ", "_")
    return [part for part in text.split("_") if part]


def _contains_any(value: str | None, tokens: set[str]) -> bool:
    text = _lower(value)
    parts = set(_tokenized_name(value))
    return bool(parts & tokens) or any(token in text for token in tokens)


def _is_description_weak(value: str | None) -> bool:
    text = _text(value)
    return not text or len(text) < 12


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _field_identity(field: FieldMeta) -> str:
    return field.field_name


class TextToSqlReadinessAssessor:
    """Assess whether table metadata is ready for Text-to-SQL systems."""

    @staticmethod
    def infer_readiness_level(score: float) -> str:
        """Map a 0-100 score to a stable Text-to-SQL readiness level."""
        if score >= 85:
            return "ready_for_text_to_sql"
        if score >= 70:
            return "usable_after_minor_metadata_completion"
        if score >= 50:
            return "govern_before_text_to_sql"
        return "not_recommended"

    @staticmethod
    def _issue(
        *,
        table_name: str,
        issue_type: str,
        severity: str,
        dimension: str,
        evidence: list[str],
        risk: str,
        suggestion: str,
        object_type: str = "table",
        object_name: str | None = None,
        requires_manual_review: bool | None = None,
    ) -> TextToSqlReadinessIssue:
        return TextToSqlReadinessIssue(
            table_name=table_name,
            issue_type=issue_type,
            severity=severity,
            dimension=dimension,
            object_type=object_type,
            object_name=object_name or table_name,
            evidence=evidence,
            risk=risk,
            suggestion=suggestion,
            requires_manual_review=(
                requires_manual_review if requires_manual_review is not None else severity in {"high", "critical"}
            ),
        )

    def _assess_table_identifiability(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        score = 100.0
        issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = []
        if not table.table_name:
            score -= 35
            issues.append(
                self._issue(
                    table_name=table.table_name or "unknown_table",
                    issue_type="missing_table_name",
                    severity="critical",
                    dimension="table_identifiability",
                    evidence=["table_name is blank"],
                    risk="Text-to-SQL cannot select a stable table target.",
                    suggestion="Provide a stable physical table name.",
                )
            )
        else:
            evidence.append(f"table_name={table.table_name}")
        if _is_description_weak(table.table_description):
            score -= 22
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="weak_table_description",
                    severity="high",
                    dimension="table_identifiability",
                    evidence=[f"table_description={table.table_description or ''}"],
                    risk="Natural-language questions may select the wrong table.",
                    suggestion="Add a business-oriented table description with object, purpose, and usage boundary.",
                )
            )
        else:
            evidence.append("table_description=available")
        if not table.table_name_cn:
            score -= 8
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_table_cn_name",
                    severity="medium",
                    dimension="table_identifiability",
                    evidence=["table_name_cn is blank"],
                    risk="Chinese business questions have weaker table matching signals.",
                    suggestion="Add a clear Chinese table name or business alias.",
                )
            )
        if not table.business_domain:
            score -= 10
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_business_domain",
                    severity="medium",
                    dimension="table_identifiability",
                    evidence=["business_domain is blank"],
                    risk="Domain routing and table filtering may become unreliable.",
                    suggestion="Bind the table to a business domain.",
                )
            )
        else:
            evidence.append(f"business_domain={table.business_domain}")
        if table.similar_table_names:
            score -= min(14, 4 * len(table.similar_table_names))
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="similar_table_confusion_risk",
                    severity="medium",
                    dimension="table_identifiability",
                    evidence=[f"similar_table_names={','.join(table.similar_table_names)}"],
                    risk="Text-to-SQL may choose a nearby but semantically different table.",
                    suggestion="Add disambiguation notes and recommended usage scenarios for similar tables.",
                    requires_manual_review=True,
                )
            )
        if _contains_any(table.table_name, TECHNICAL_TABLE_TOKENS) or _lower(table.lifecycle_status) in {
            "tmp",
            "temporary",
            "deprecated",
            "retired",
            "inactive",
        }:
            score -= 20
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="technical_or_lifecycle_table",
                    severity="high",
                    dimension="table_identifiability",
                    evidence=[f"table_name={table.table_name}", f"lifecycle_status={table.lifecycle_status or ''}"],
                    risk="Temporary, test, log, or retired tables may pollute table selection.",
                    suggestion="Exclude the table from Text-to-SQL candidates or clarify its lifecycle boundary.",
                )
            )
        return _clamp(score), issues, evidence

    def _assess_field_understandability(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        if not table.fields:
            return (
                20.0,
                [
                    self._issue(
                        table_name=table.table_name,
                        issue_type="missing_field_list",
                        severity="critical",
                        dimension="field_understandability",
                        evidence=["fields is empty"],
                        risk="Text-to-SQL cannot select columns without field metadata.",
                        suggestion="Provide the field list with names, descriptions, and data types.",
                    )
                ],
                [],
            )
        issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = [f"field_count={len(table.fields)}"]
        missing_cn = [field for field in table.fields if not field.field_name_cn]
        weak_descriptions = [
            field for field in table.fields if _is_description_weak(field.field_description)
        ]
        ambiguous = [
            field
            for field in table.fields
            if _contains_any(field.field_name, AMBIGUOUS_FIELD_TOKENS)
            and (_is_description_weak(field.field_description) or not field.field_name_cn)
        ]
        duplicate_cn = [
            name
            for name, count in Counter(
                _lower(field.field_name_cn) for field in table.fields if field.field_name_cn
            ).items()
            if count > 1
        ]
        score = 100.0
        score -= min(32, 32 * len(weak_descriptions) / max(1, len(table.fields)))
        score -= min(18, 18 * len(missing_cn) / max(1, len(table.fields)))
        score -= min(16, 3 * len(ambiguous))
        score -= min(12, 6 * len(duplicate_cn))
        if weak_descriptions:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="weak_field_descriptions",
                    severity="high",
                    dimension="field_understandability",
                    object_type="field",
                    object_name=f"{table.table_name}.{_field_identity(weak_descriptions[0])}",
                    evidence=[f"weak_description_count={len(weak_descriptions)}"],
                    risk="The model may select wrong fields or infer meaning from technical names only.",
                    suggestion="Complete field descriptions, especially for core IDs, dates, amounts, and status fields.",
                )
            )
        if missing_cn:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_field_cn_names",
                    severity="medium",
                    dimension="field_understandability",
                    object_type="field",
                    object_name=f"{table.table_name}.{_field_identity(missing_cn[0])}",
                    evidence=[f"missing_cn_count={len(missing_cn)}"],
                    risk="Chinese questions have weaker column matching signals.",
                    suggestion="Add Chinese names or business aliases for fields.",
                )
            )
        if ambiguous:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="ambiguous_field_names",
                    severity="medium",
                    dimension="field_understandability",
                    object_type="field",
                    object_name=f"{table.table_name}.{_field_identity(ambiguous[0])}",
                    evidence=[f"ambiguous_fields={','.join(field.field_name for field in ambiguous[:8])}"],
                    risk="Generic fields such as status, type, flag, amount, or date can be misused.",
                    suggestion="Add explicit business meaning, value domain, and usage notes for ambiguous fields.",
                    requires_manual_review=True,
                )
            )
        if duplicate_cn:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="synonym_or_duplicate_field_label",
                    severity="medium",
                    dimension="field_understandability",
                    evidence=[f"duplicate_field_labels={','.join(duplicate_cn[:8])}"],
                    risk="Text-to-SQL may confuse fields that share the same business label.",
                    suggestion="Disambiguate field labels or document the intended usage for each field.",
                    requires_manual_review=True,
                )
            )
        return _clamp(score), issues, evidence

    def _assess_relationship_inferability(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = []
        pk_fields = set(table.primary_key_fields) | {
            field.field_name for field in table.fields if field.is_primary_key
        }
        fk_fields = set(table.foreign_key_fields) | {
            field.field_name for field in table.fields if field.is_foreign_key
        }
        relationships = table.relationships
        score = 58.0
        if pk_fields:
            score += 16
            evidence.append(f"primary_key_fields={','.join(sorted(pk_fields))}")
        else:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_primary_key",
                    severity="high",
                    dimension="relationship_inferability",
                    evidence=["no primary key metadata"],
                    risk="The model may generate duplicate-prone joins or fail to identify table grain.",
                    suggestion="Declare primary key or table grain fields.",
                )
            )
        if fk_fields:
            score += 10
            evidence.append(f"foreign_key_fields={','.join(sorted(fk_fields))}")
        if relationships:
            valid_relationships = [
                relation
                for relation in relationships
                if relation.source_field and relation.target_field and relation.target_table
            ]
            score += 16 if valid_relationships else 6
            evidence.append(f"relationship_count={len(relationships)}")
        elif fk_fields:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_relationship_description",
                    severity="medium",
                    dimension="relationship_inferability",
                    evidence=["foreign keys exist but relationships are not described"],
                    risk="Text-to-SQL may choose an incorrect join path.",
                    suggestion="Add relationship metadata with target table, join fields, and relationship type.",
                )
            )
        else:
            score -= 18
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_join_signals",
                    severity="high",
                    dimension="relationship_inferability",
                    evidence=["no foreign key or relationship metadata"],
                    risk="Multi-table questions may generate invalid joins.",
                    suggestion="Document common join paths and fact/dimension relationships.",
                )
            )
        return _clamp(score), issues, evidence

    def _assess_metric_clarity(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        metric_like_fields = [
            field
            for field in table.fields
            if _contains_any(field.field_name, {"amt", "amount", "rate", "ratio", "cnt", "count", "num", "qty"})
        ]
        if not metric_like_fields and not table.metric_definitions:
            return 82.0, [], ["no obvious metric-like fields"]
        issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = []
        score = 60.0
        if table.metric_definitions:
            evidence.append(f"metric_definition_count={len(table.metric_definitions)}")
            complete = [
                metric
                for metric in table.metric_definitions
                if metric.description and (metric.unit or metric.filters or metric.time_grain or metric.status_scope)
            ]
            score += min(30, 12 + 18 * len(complete) / max(1, len(table.metric_definitions)))
            incomplete = len(table.metric_definitions) - len(complete)
            if incomplete:
                score -= min(16, incomplete * 4)
                issues.append(
                    self._issue(
                        table_name=table.table_name,
                        issue_type="incomplete_metric_definition",
                        severity="medium",
                        dimension="metric_clarity",
                        evidence=[f"incomplete_metric_definition_count={incomplete}"],
                        risk="The model may calculate metrics with wrong filters, units, or time windows.",
                        suggestion="Complete metric formula, filter, unit, time grain, and status scope.",
                        requires_manual_review=True,
                    )
                )
        else:
            score -= min(28, 6 * len(metric_like_fields))
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_metric_definitions",
                    severity="high",
                    dimension="metric_clarity",
                    evidence=[f"metric_like_fields={','.join(field.field_name for field in metric_like_fields[:8])}"],
                    risk="Text-to-SQL may aggregate amount, rate, count, or quantity fields with the wrong business meaning.",
                    suggestion="Add metric definitions for measurable fields, including unit, filters, and time/status scope.",
                )
            )
        return _clamp(score), issues, evidence

    def _assess_enum_explainability(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        enum_like_fields = [
            field for field in table.fields if _contains_any(field.field_name, ENUM_FIELD_TOKENS)
        ]
        if not enum_like_fields:
            return 86.0, [], ["no obvious enum-like fields"]
        explained = [
            field
            for field in enum_like_fields
            if field.field_name in table.enum_definitions and table.enum_definitions[field.field_name]
        ]
        coverage = len(explained) / max(1, len(enum_like_fields))
        score = 45 + 55 * coverage
        issues: list[TextToSqlReadinessIssue] = []
        evidence = [
            f"enum_like_field_count={len(enum_like_fields)}",
            f"enum_explanation_coverage={coverage:.0%}",
        ]
        if coverage < 1:
            missing = [field.field_name for field in enum_like_fields if field.field_name not in table.enum_definitions]
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_enum_value_explanations",
                    severity="high" if coverage == 0 else "medium",
                    dimension="enum_explainability",
                    object_type="field",
                    object_name=f"{table.table_name}.{missing[0] if missing else enum_like_fields[0].field_name}",
                    evidence=[f"missing_enum_fields={','.join(missing[:8])}"],
                    risk="The model may filter status, type, flag, or code fields with incorrect values.",
                    suggestion="Add value-domain mappings such as code to business meaning for enum-like fields.",
                    requires_manual_review=True,
                )
            )
        return _clamp(score), issues, evidence

    def _assess_security_permission_fit(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = []
        sensitive_fields = [
            field
            for field in table.fields
            if field.is_sensitive or _contains_any(field.field_name, SENSITIVE_FIELD_TOKENS)
        ]
        score = 84.0
        if table.permission_label:
            score += 6
            evidence.append(f"permission_label={table.permission_label}")
        else:
            score -= 14
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_permission_label",
                    severity="high",
                    dimension="security_permission_fit",
                    evidence=["permission_label is blank"],
                    risk="Generated SQL may expose tables outside the user's permission boundary.",
                    suggestion="Add table-level permission labels for Text-to-SQL filtering.",
                )
            )
        if table.sensitivity_label:
            score += 4
            evidence.append(f"sensitivity_label={table.sensitivity_label}")
        if sensitive_fields and not table.sensitivity_label:
            score -= min(18, 6 * len(sensitive_fields))
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="sensitive_fields_without_table_label",
                    severity="high",
                    dimension="security_permission_fit",
                    object_type="field",
                    object_name=f"{table.table_name}.{sensitive_fields[0].field_name}",
                    evidence=[f"sensitive_field_count={len(sensitive_fields)}"],
                    risk="Text-to-SQL may generate queries over sensitive columns without explicit controls.",
                    suggestion="Label sensitive fields and set table-level sensitivity or masking policy.",
                )
            )
        if sensitive_fields and not table.masking_policy:
            score -= 8
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_masking_policy",
                    severity="medium",
                    dimension="security_permission_fit",
                    evidence=["sensitive fields exist but masking_policy is blank"],
                    risk="Generated SQL may return raw sensitive values.",
                    suggestion="Document masking or exclusion policy for sensitive fields.",
                )
            )
        return _clamp(score), issues, evidence

    def _assess_query_example_support(
        self,
        table: TextToSqlTableMetadata,
    ) -> tuple[float, list[TextToSqlReadinessIssue], list[str]]:
        examples = table.sample_sql
        query_logs = [item for item in table.query_log_examples if _text(item)]
        score = 45.0
        evidence: list[str] = []
        if examples:
            examples_with_sql = [item for item in examples if item.sql]
            score += 28 if examples_with_sql else 14
            evidence.append(f"sample_sql_count={len(examples)}")
            if any(item.business_explanation for item in examples):
                score += 8
            if any(item.failure_mode for item in examples):
                score += 6
        if query_logs:
            score += min(13, 4 * len(query_logs))
            evidence.append(f"query_log_example_count={len(query_logs)}")
        issues: list[TextToSqlReadinessIssue] = []
        if not examples and not query_logs:
            issues.append(
                self._issue(
                    table_name=table.table_name,
                    issue_type="missing_text_to_sql_examples",
                    severity="medium",
                    dimension="query_example_support",
                    evidence=["sample_sql and query_log_examples are empty"],
                    risk="The model has no grounded examples for common questions or expected SQL style.",
                    suggestion="Add common questions, sample SQL, business explanation, and known bad SQL cases.",
                )
            )
        return _clamp(score), issues, evidence

    def _score_table(self, table: TextToSqlTableMetadata) -> tuple[TextToSqlReadinessScore, list[TextToSqlReadinessIssue]]:
        dimension_scores: dict[str, float] = {}
        all_issues: list[TextToSqlReadinessIssue] = []
        evidence: list[str] = []
        for dimension, evaluator in [
            ("table_identifiability", self._assess_table_identifiability),
            ("field_understandability", self._assess_field_understandability),
            ("relationship_inferability", self._assess_relationship_inferability),
            ("metric_clarity", self._assess_metric_clarity),
            ("enum_explainability", self._assess_enum_explainability),
            ("security_permission_fit", self._assess_security_permission_fit),
            ("query_example_support", self._assess_query_example_support),
        ]:
            score, issues, dimension_evidence = evaluator(table)
            dimension_scores[dimension] = score
            all_issues.extend(issues)
            evidence.extend(dimension_evidence)

        overall = _clamp(sum(dimension_scores.values()) / len(DIMENSIONS))
        level = self.infer_readiness_level(overall)
        major_gaps = _dedupe(
            issue.issue_type for issue in all_issues if issue.severity in {"high", "critical"}
        )
        risks = _dedupe(issue.risk or "" for issue in all_issues if issue.risk)
        recommendations = _dedupe(issue.suggestion or "" for issue in all_issues if issue.suggestion)
        return (
            TextToSqlReadinessScore(
                table_name=table.table_name,
                readiness_score=overall,
                readiness_level=level,
                dimension_scores=dimension_scores,
                major_gaps=major_gaps,
                risks=risks,
                recommendations=recommendations,
                evidence=_dedupe(evidence),
                requires_manual_review=any(issue.requires_manual_review for issue in all_issues),
            ),
            all_issues,
        )

    @staticmethod
    def _summary(
        scores: list[TextToSqlReadinessScore],
        issues: list[TextToSqlReadinessIssue],
    ) -> dict[str, object]:
        level_counts = Counter(score.readiness_level for score in scores)
        severity_counts = Counter(issue.severity for issue in issues)
        dimension_issue_counts = Counter(issue.dimension for issue in issues)
        avg_score = (
            round(sum(score.readiness_score for score in scores) / len(scores), 2)
            if scores
            else 0.0
        )
        return {
            "table_count": len(scores),
            "issue_count": len(issues),
            "average_readiness_score": avg_score,
            "level_counts": dict(level_counts),
            "severity_counts": dict(severity_counts),
            "dimension_issue_counts": dict(dimension_issue_counts),
            "not_recommended_count": level_counts.get("not_recommended", 0),
            "ready_count": level_counts.get("ready_for_text_to_sql", 0),
        }

    def assess(
        self,
        tables: list[TextToSqlTableMetadata],
    ) -> TextToSqlReadinessAssessmentResult:
        """Run local Text-to-SQL readiness checks for table metadata."""
        scores: list[TextToSqlReadinessScore] = []
        issues: list[TextToSqlReadinessIssue] = []
        for table in tables:
            table_score, table_issues = self._score_table(table)
            scores.append(table_score)
            issues.extend(table_issues)
        return TextToSqlReadinessAssessmentResult(
            table_count=len(tables),
            issue_count=len(issues),
            scores=scores,
            issues=issues,
            summary=self._summary(scores, issues),
        )

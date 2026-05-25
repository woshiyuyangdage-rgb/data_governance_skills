"""Rule-based AI-ready scoring for governed data assets."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

from app.core.governance.readiness_assessor import ReadinessAssessor
from app.core.models.ai_ready_score import AiReadyScore
from app.core.models.issue import Issue
from app.core.models.workflow_result import WorkflowResult

DIMENSION_NAMES = [
    "discoverability",
    "understandability",
    "semantic_consistency",
    "standardization",
    "quality_controllability",
    "security_controllability",
    "traceability",
    "ai_application_adaptability",
]

ISSUE_PENALTIES = {
    "low": 3.0,
    "medium": 7.0,
    "high": 12.0,
    "critical": 18.0,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, round(value, 2)))


def _table_from_object_name(object_name: str | None) -> str:
    text = str(object_name or "overall").strip()
    return text.split(".", 1)[0] if "." in text else text or "overall"


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


class AiReadyAssessor:
    """Assess whether table assets are suitable for AI consumption."""

    @staticmethod
    def infer_ai_ready_level(score: float) -> str:
        """Map a 0-100 score to a stable AI-ready level."""
        if score >= 85:
            return "A_ai_ready"
        if score >= 70:
            return "B_basically_usable"
        if score >= 50:
            return "C_govern_before_use"
        return "D_not_recommended_for_ai"

    @staticmethod
    def _issues_by_table(issues: list[Issue]) -> dict[str, list[Issue]]:
        grouped: dict[str, list[Issue]] = defaultdict(list)
        for issue in issues:
            grouped[_table_from_object_name(issue.object_name)].append(issue)
        return grouped

    @staticmethod
    def _table_names(result: WorkflowResult) -> list[str]:
        tables = set(ReadinessAssessor.collect_table_names(result))
        for item in result.field_description_suggestions:
            tables.add(item.table_name)
        for item in result.table_semantic_summaries:
            tables.add(item.table_name)
        if result.execution_ready_package is not None:
            for rule in result.execution_ready_package.rules:
                tables.add(rule.source_table_name)
        return sorted(table for table in tables if table and table != "overall")

    @staticmethod
    def _issue_penalty(issues: list[Issue], issue_types: set[str]) -> float:
        penalty = 0.0
        for issue in issues:
            if issue.issue_type not in issue_types:
                continue
            penalty += ISSUE_PENALTIES.get(str(issue.severity).lower(), 6.0)
        return penalty

    @staticmethod
    def _has_issue(issues: list[Issue], issue_types: set[str]) -> bool:
        return any(issue.issue_type in issue_types for issue in issues)

    def _score_discoverability(
        self,
        table_name: str,
        issues: list[Issue],
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 72.0
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        if summary is not None:
            evidence.append("table semantic summary available")
            if summary.business_domain:
                score += 8
            if summary.key_concepts:
                score += 6
            if summary.table_name_cn:
                score += 4
        if any(item.table_name == table_name for item in result.field_description_suggestions):
            score += 4
            evidence.append("field labels/descriptions are available for discovery")
        penalty = self._issue_penalty(
            issues,
            {
                "missing_metadata_defect",
                "business_ownership_defect",
                "missing_table_cn_name",
                "missing_table_description",
                "business_domain_missing",
                "technical_object_defect",
            },
        )
        score -= penalty
        if penalty:
            actions.append("Complete table label, business domain, catalog tags, and lifecycle metadata.")
        return _clamp(score)

    def _score_understandability(
        self,
        table_name: str,
        issues: list[Issue],
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 58.0
        fields = [
            item
            for item in result.field_description_suggestions
            if item.table_name == table_name
        ]
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        if summary is not None:
            score += 16
            evidence.append("table business summary generated")
            if summary.business_object:
                score += 5
            if summary.core_fields:
                score += 5
            if summary.confidence >= 0.75:
                score += 5
        if fields:
            usable = [
                item
                for item in fields
                if "description_usable" in item.quality_tags
                or not item.requires_manual_review
            ]
            coverage = len(usable) / max(1, len(fields))
            score += 16 * coverage
            evidence.append(f"field description coverage={coverage:.0%}")
        penalty = self._issue_penalty(
            issues,
            {
                "missing_metadata_defect",
                "missing_field_description",
                "description_same_as_name",
                "placeholder_description",
                "suspicious_short_description",
            },
        )
        score -= penalty
        if penalty:
            actions.append("Complete field explanations and table summaries so AI does not rely on technical names only.")
        return _clamp(score)

    def _score_semantic_consistency(
        self,
        table_name: str,
        issues: list[Issue],
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 82.0
        mappings = [item for item in result.mapping_results if item.table_name == table_name]
        low_confidence = [item for item in mappings if item.match_score < 0.7]
        wrong_mapping_issues = self._has_issue(
            issues,
            {"standard_mapping_suspected_wrong", "semantic_consistency_defect"},
        )
        if mappings:
            evidence.append(f"standard mapping candidates={len(mappings)}")
            score += min(8, len(mappings))
        score -= min(18, len(low_confidence) * 4)
        if low_confidence:
            actions.append("Review low-confidence standard mappings to avoid semantic drift.")
        if wrong_mapping_issues:
            score -= 12
            actions.append("Prioritize semantic consistency defects and suspected wrong mappings.")
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        if summary is not None and summary.requires_manual_review:
            score -= 5
        return _clamp(score)

    def _score_standardization(
        self,
        table_name: str,
        issues: list[Issue],
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 62.0
        mapped = [item for item in result.mapping_results if item.table_name == table_name]
        confirmed = [
            item for item in result.confirmed_mapping_results if item.table_name == table_name
        ]
        unmapped = [item for item in result.unmapped_fields if item.table_name == table_name]
        field_descriptions = [
            item
            for item in result.field_description_suggestions
            if item.table_name == table_name
        ]
        standard_refs = [
            item
            for item in field_descriptions
            if item.standard_code or item.standard_name
        ]
        score += min(18, len(mapped) * 3)
        score += min(10, len(confirmed) * 4)
        if field_descriptions:
            score += 10 * (len(standard_refs) / max(1, len(field_descriptions)))
        score -= min(28, len(unmapped) * 7)
        score -= self._issue_penalty(
            issues,
            {"standard_mapping_missing", "standard_mapping_low_confidence"},
        )
        if mapped or confirmed or standard_refs:
            evidence.append("data standard mapping evidence available")
        if unmapped:
            actions.append("Map unmapped fields and enrich synonyms, abbreviations, and standard candidates.")
        return _clamp(score)

    def _score_quality_controllability(
        self,
        table_name: str,
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        suggestions = [
            item for item in result.quality_rule_suggestions if item.source_table_name == table_name
        ]
        cross_field = [
            item for item in result.cross_field_quality_rules if item.source_table_name == table_name
        ]
        confirmed = [
            item for item in result.confirmed_quality_rules if item.source_table_name == table_name
        ]
        execution_rules = []
        if result.execution_ready_package is not None:
            execution_rules = [
                item
                for item in result.execution_ready_package.rules
                if item.source_table_name == table_name
            ]
        total_candidates = len(suggestions) + len(cross_field)
        score = 45.0
        score += min(24, total_candidates * 4)
        score += min(20, len(confirmed) * 6)
        score += min(8, len(execution_rules) * 2)
        low_confidence = [
            item
            for item in [*suggestions, *cross_field]
            if item.confidence is not None and item.confidence < 0.5
        ]
        score -= min(15, len(low_confidence) * 5)
        if total_candidates or confirmed:
            evidence.append(
                f"quality rule candidates={total_candidates}, confirmed={len(confirmed)}"
            )
        if not total_candidates and not confirmed:
            actions.append("Add quality rules for core identifiers, status, date, and amount fields.")
        elif total_candidates and not confirmed:
            actions.append("Confirm recommended quality rules and build the execution-ready package.")
        return _clamp(score)

    def _score_security_controllability(
        self,
        issues: list[Issue],
        result: WorkflowResult,
        table_name: str,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 82.0
        sensitive_or_ai_risk = [
            issue
            for issue in issues
            if issue.issue_type in {"sensitive_field_unlabeled", "ai_consumption_risk_defect"}
            or bool(issue.ai_risk)
        ]
        score -= min(40, len(sensitive_or_ai_risk) * 10)
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        if summary is not None and summary.ai_usage_risks:
            joined = " ".join(summary.ai_usage_risks).lower()
            if "sensitive" in joined or "access" in joined:
                score -= 10
                actions.append("Add sensitivity labels, masking notes, and AI access boundaries.")
            else:
                score += 5
            evidence.append("AI usage risk notes available")
        if not sensitive_or_ai_risk and not actions:
            evidence.append("no explicit sensitive-field AI risk issue detected")
        return _clamp(score)

    def _score_traceability(
        self,
        table_name: str,
        issues: list[Issue],
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 56.0
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        summary_evidence = " | ".join(summary.evidence).lower() if summary else ""
        if "upstream_system" in summary_evidence:
            score += 10
            evidence.append("upstream/source evidence available")
        if "downstream_applications" in summary_evidence:
            score += 8
            evidence.append("downstream application evidence available")
        if "data_layer" in summary_evidence:
            score += 6
        if "primary_key_fields" in summary_evidence:
            score += 6
        if "foreign_key_fields" in summary_evidence:
            score += 4
        if "frequent_query_sql" in summary_evidence:
            score += 4
        score -= self._issue_penalty(
            issues,
            {
                "business_ownership_defect",
                "owner_role_missing",
                "lifecycle_status_missing",
            },
        )
        if score < 70:
            actions.append("Add source system, lineage, update time, owner, and version metadata.")
        return _clamp(score)

    def _score_ai_application_adaptability(
        self,
        table_name: str,
        result: WorkflowResult,
        evidence: list[str],
        actions: list[str],
    ) -> float:
        score = 50.0
        summary = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        fields = [
            item
            for item in result.field_description_suggestions
            if item.table_name == table_name
        ]
        stg_fields = [
            item
            for item in result.stg_field_suggestions + result.confirmed_stg_suggestions
            if item.source_table_name == table_name
        ]
        if summary is not None:
            score += 16
            if summary.applicable_scenarios:
                score += 6
            if summary.ai_usage_risks:
                score += 4
            if summary.recommended_actions:
                score += 4
            evidence.append("table summary can be used as AI context")
        if fields:
            score += min(12, len(fields))
        if stg_fields:
            score += min(8, len(stg_fields) * 2)
        if result.execution_ready_package is not None:
            rules = [
                item
                for item in result.execution_ready_package.rules
                if item.source_table_name == table_name
            ]
            if rules:
                score += min(8, len(rules) * 2)
        if score < 70:
            actions.append("Add table relationships, sample queries, usage limits, and AI-ready semantic context.")
        return _clamp(score)

    def build_table_score(
        self,
        table_name: str,
        result: WorkflowResult,
        issues_by_table: dict[str, list[Issue]],
    ) -> AiReadyScore:
        """Build one table-level AI-ready score."""
        issues = issues_by_table.get(table_name, [])
        evidence: list[str] = []
        actions: list[str] = []
        risks: list[str] = []
        dimension_scores = {
            "discoverability": self._score_discoverability(
                table_name,
                issues,
                result,
                evidence,
                actions,
            ),
            "understandability": self._score_understandability(
                table_name,
                issues,
                result,
                evidence,
                actions,
            ),
            "semantic_consistency": self._score_semantic_consistency(
                table_name,
                issues,
                result,
                evidence,
                actions,
            ),
            "standardization": self._score_standardization(
                table_name,
                issues,
                result,
                evidence,
                actions,
            ),
            "quality_controllability": self._score_quality_controllability(
                table_name,
                result,
                evidence,
                actions,
            ),
            "security_controllability": self._score_security_controllability(
                issues,
                result,
                table_name,
                evidence,
                actions,
            ),
            "traceability": self._score_traceability(
                table_name,
                issues,
                result,
                evidence,
                actions,
            ),
            "ai_application_adaptability": self._score_ai_application_adaptability(
                table_name,
                result,
                evidence,
                actions,
            ),
        }
        for name, score in dimension_scores.items():
            if score < 60:
                risks.append(f"{name} below 60")
        for issue in issues:
            if issue.ai_risk:
                risks.append(issue.ai_risk)
        summary_obj = next(
            (item for item in result.table_semantic_summaries if item.table_name == table_name),
            None,
        )
        if summary_obj is not None:
            risks.extend(
                risk
                for risk in summary_obj.ai_usage_risks
                if risk != "no obvious AI consumption risk detected"
            )
            actions.extend(summary_obj.recommended_actions)

        overall_score = _clamp(mean(dimension_scores.values()))
        level = self.infer_ai_ready_level(overall_score)
        return AiReadyScore(
            object_type="table",
            object_name=table_name,
            overall_score=overall_score,
            ai_ready_level=level,
            dimension_scores=dimension_scores,
            evidence=_dedupe(evidence)[:12],
            risk_flags=_dedupe(risks)[:12],
            recommended_actions=_dedupe(actions)[:12],
            summary=(
                f"{table_name} AI-ready score is {overall_score:.0f} "
                f"with level {level}."
            ),
        )

    def assess(self, result: WorkflowResult) -> list[AiReadyScore]:
        """Build table-level AI-ready scores plus an overall score."""
        table_names = self._table_names(result)
        issues_by_table = self._issues_by_table(result.issues)
        table_scores = [
            self.build_table_score(table_name, result, issues_by_table)
            for table_name in table_names
        ]
        if not table_scores:
            return [
                AiReadyScore(
                    object_type="overall",
                    object_name="overall",
                    overall_score=0.0,
                    ai_ready_level="D_not_recommended_for_ai",
                    dimension_scores={},
                    risk_flags=["no governance outputs available"],
                    recommended_actions=[
                        "Run metadata diagnosis, semantic enrichment, mapping, and quality rule recommendation first."
                    ],
                    summary="No governance outputs were available for AI-ready scoring.",
                )
            ]

        overall_dimensions = {
            name: _clamp(mean(score.dimension_scores.get(name, 0.0) for score in table_scores))
            for name in DIMENSION_NAMES
        }
        overall_score = _clamp(mean(score.overall_score for score in table_scores))
        overall = AiReadyScore(
            object_type="overall",
            object_name="overall",
            overall_score=overall_score,
            ai_ready_level=self.infer_ai_ready_level(overall_score),
            dimension_scores=overall_dimensions,
            evidence=[f"table_count={len(table_scores)}"],
            risk_flags=_dedupe(
                [flag for score in table_scores for flag in score.risk_flags]
            )[:12],
            recommended_actions=_dedupe(
                [action for score in table_scores for action in score.recommended_actions]
            )[:12],
            summary=(
                f"Overall AI-ready score is {overall_score:.0f} across "
                f"{len(table_scores)} tables."
            ),
        )
        return table_scores + [overall]

    @staticmethod
    def summarize(scores: list[AiReadyScore]) -> dict[str, object]:
        """Return a compact AI-ready summary."""
        level_counts: dict[str, int] = {}
        for score in scores:
            level_counts[score.ai_ready_level] = level_counts.get(score.ai_ready_level, 0) + 1
        overall = next((score for score in scores if score.object_type == "overall"), None)
        return {
            "ai_ready_score_count": len(scores),
            "ai_ready_level_counts": level_counts,
            "overall_score": overall.overall_score if overall else None,
            "overall_ai_ready_level": overall.ai_ready_level if overall else None,
            "dimensions": list(DIMENSION_NAMES),
        }

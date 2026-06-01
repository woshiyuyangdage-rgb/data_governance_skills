"""Rule-based governance gap classification."""

from collections import defaultdict
from typing import Any

from app.core.governance.readiness_assessor import _table_from_object_name
from app.core.models.governance_gap import GovernanceGap
from app.core.models.workflow_result import WorkflowResult
from app.core.rules.config_loader import (
    get_governance_gap_taxonomy_config,
    get_remediation_templates_config,
)

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}
AI_READY_DIMENSION_GAPS = {
    "discoverability": ("metadata_completion_gap", "metadata"),
    "understandability": ("metadata_completion_gap", "metadata"),
    "semantic_consistency": ("semantic_consistency_gap", "semantic"),
    "standardization": ("standard_mapping_gap", "mapping"),
    "quality_controllability": ("quality_rule_gap", "quality"),
    "security_controllability": ("ai_consumption_risk_gap", "ai"),
    "traceability": ("business_ownership_gap", "metadata"),
    "ai_application_adaptability": ("ai_consumption_risk_gap", "ai"),
}
RAG_CATEGORY_GAPS = {
    "metadata_tags": ("metadata_completion_gap", "metadata"),
    "document_quality": ("ai_consumption_risk_gap", "ai"),
    "chunk_quality": ("ai_consumption_risk_gap", "ai"),
    "retrieval_quality": ("semantic_consistency_gap", "semantic"),
    "answer_quality": ("ai_consumption_risk_gap", "ai"),
    "permission_risk": ("ai_consumption_risk_gap", "ai"),
}
TEXT_TO_SQL_DIMENSION_GAPS = {
    "table_identifiability": ("metadata_completion_gap", "metadata"),
    "field_understandability": ("metadata_completion_gap", "metadata"),
    "relationship_inferability": ("semantic_consistency_gap", "semantic"),
    "metric_clarity": ("semantic_consistency_gap", "semantic"),
    "enum_explainability": ("semantic_consistency_gap", "semantic"),
    "security_permission_fit": ("ai_consumption_risk_gap", "ai"),
    "query_example_support": ("ai_consumption_risk_gap", "ai"),
}


class GapClassifier:
    """Classify raw governance signals into aggregated governance gaps."""

    def __init__(
        self,
        taxonomy: dict[str, Any] | None = None,
        remediation_templates: dict[str, Any] | None = None,
    ) -> None:
        self.taxonomy = taxonomy or get_governance_gap_taxonomy_config()
        self.remediation_templates = remediation_templates or get_remediation_templates_config()

    def _source_to_gap(self) -> dict[str, tuple[str, str]]:
        mapping: dict[str, tuple[str, str]] = {}
        for gap in self.taxonomy.get("gaps", []):
            if not isinstance(gap, dict):
                continue
            gap_type = str(gap.get("gap_type", "")).strip()
            category = str(gap.get("category", "")).strip()
            for source in gap.get("sources", []):
                mapping[str(source)] = (gap_type, category)
        return mapping

    def _owner_for_gap(self, gap_type: str) -> str | None:
        templates = self.remediation_templates.get("templates", {})
        template = templates.get(gap_type, {}) if isinstance(templates, dict) else {}
        return str(template.get("owner_role")) if isinstance(template, dict) and template.get("owner_role") else None

    @staticmethod
    def _stronger_severity(left: str, right: str) -> str:
        return left if SEVERITY_RANK.get(left, 1) >= SEVERITY_RANK.get(right, 1) else right

    def _add_signal(
        self,
        bucket: dict[tuple[str, str, str], dict[str, Any]],
        object_name: str,
        gap_type: str,
        category: str,
        severity: str,
        source_signal: str,
        reason: str,
        affected_object: str | None = None,
        object_type: str = "table",
    ) -> None:
        key = (object_type, object_name, gap_type)
        if key not in bucket:
            bucket[key] = {
                "object_type": object_type,
                "object_name": object_name,
                "gap_type": gap_type,
                "category": category,
                "severity": severity or "low",
                "source_signals": set(),
                "signal_counts": defaultdict(int),
                "severity_counts": defaultdict(int),
                "affected_objects": set(),
                "reasons": [],
            }
        bucket[key]["severity"] = self._stronger_severity(
            str(bucket[key]["severity"]),
            severity or "low",
        )
        bucket[key]["source_signals"].add(source_signal)
        bucket[key]["signal_counts"][source_signal] += 1
        bucket[key]["severity_counts"][severity or "low"] += 1
        if affected_object:
            bucket[key]["affected_objects"].add(affected_object)
        if reason:
            bucket[key]["reasons"].append(reason)

    @staticmethod
    def _severity_from_score(score: float, *, high_below: float = 50.0) -> str:
        if score < high_below:
            return "high"
        return "medium"

    def _add_ai_ready_signals(
        self,
        bucket: dict[tuple[str, str, str], dict[str, Any]],
        result: WorkflowResult,
    ) -> None:
        for score in result.ai_ready_scores:
            if score.object_name == "overall":
                continue
            object_type = score.object_type or "table"
            if score.overall_score < 70:
                self._add_signal(
                    bucket,
                    score.object_name,
                    "ai_consumption_risk_gap",
                    "ai",
                    self._severity_from_score(score.overall_score),
                    "ai_ready_below_target",
                    score.summary
                    or f"AI-ready score is {score.overall_score:.0f}, below target.",
                    affected_object=score.object_name,
                    object_type=object_type,
                )
            for dimension, dimension_score in score.dimension_scores.items():
                if dimension_score >= 60:
                    continue
                gap_type, category = AI_READY_DIMENSION_GAPS.get(
                    dimension,
                    ("ai_consumption_risk_gap", "ai"),
                )
                self._add_signal(
                    bucket,
                    score.object_name,
                    gap_type,
                    category,
                    self._severity_from_score(dimension_score, high_below=45.0),
                    f"ai_ready_low_{dimension}",
                    (
                        f"AI-ready dimension {dimension} is "
                        f"{dimension_score:.0f}, below 60."
                    ),
                    affected_object=score.object_name,
                    object_type=object_type,
                )

    def _add_rag_quality_signals(
        self,
        bucket: dict[tuple[str, str, str], dict[str, Any]],
        result: WorkflowResult,
    ) -> None:
        for issue in result.rag_quality_issues:
            if issue.severity not in {"high", "critical"} and not issue.requires_manual_review:
                continue
            gap_type, category = RAG_CATEGORY_GAPS.get(
                issue.category or "",
                ("ai_consumption_risk_gap", "ai"),
            )
            self._add_signal(
                bucket,
                issue.object_name,
                gap_type,
                category,
                issue.severity,
                f"rag_quality_{issue.issue_type}",
                issue.suggestion or issue.risk or issue.issue_type,
                affected_object=issue.object_name,
                object_type=issue.object_type or "rag_object",
            )

    def _add_text_to_sql_signals(
        self,
        bucket: dict[tuple[str, str, str], dict[str, Any]],
        result: WorkflowResult,
    ) -> None:
        for score in result.text_to_sql_readiness_scores:
            if score.readiness_score >= 70:
                continue
            self._add_signal(
                bucket,
                score.table_name,
                "ai_consumption_risk_gap",
                "ai",
                self._severity_from_score(score.readiness_score),
                "text_to_sql_readiness_below_target",
                (
                    f"Text-to-SQL readiness is {score.readiness_score:.0f} "
                    f"with level {score.readiness_level}."
                ),
                affected_object=score.table_name,
            )
        for issue in result.text_to_sql_readiness_issues:
            if issue.severity not in {"medium", "high", "critical"} and not issue.requires_manual_review:
                continue
            gap_type, category = TEXT_TO_SQL_DIMENSION_GAPS.get(
                issue.dimension,
                ("ai_consumption_risk_gap", "ai"),
            )
            self._add_signal(
                bucket,
                issue.table_name,
                gap_type,
                category,
                issue.severity,
                f"text_to_sql_{issue.issue_type}",
                issue.suggestion or issue.risk or issue.issue_type,
                affected_object=issue.object_name or issue.table_name,
            )

    def classify(self, result: WorkflowResult) -> list[GovernanceGap]:
        """Classify workflow signals into table-level governance gaps."""
        source_to_gap = self._source_to_gap()
        bucket: dict[tuple[str, str, str], dict[str, Any]] = {}

        for issue in result.issues:
            mapped = source_to_gap.get(issue.issue_type)
            if not mapped:
                continue
            gap_type, category = mapped
            self._add_signal(
                bucket,
                _table_from_object_name(issue.object_name),
                gap_type,
                category,
                issue.severity,
                issue.issue_type,
                issue.suggestion or issue.issue_type,
                affected_object=issue.object_name,
            )

        for item in result.unmapped_fields:
            source_signal = (
                "standard_mapping_low_confidence"
                if item.best_candidate_score is not None and item.best_candidate_score > 0
                else "standard_mapping_missing"
            )
            gap_type, category = source_to_gap.get(
                source_signal,
                ("standard_mapping_gap", "mapping"),
            )
            self._add_signal(
                bucket,
                item.table_name,
                gap_type,
                category,
                "medium",
                source_signal,
                item.reason or "Field requires standard mapping review.",
                affected_object=f"{item.table_name}.{item.field_name}",
            )

        for suggestion in result.stg_field_suggestions:
            if suggestion.match_score is not None and suggestion.match_score < 0.7:
                gap_type, category = source_to_gap.get(
                    "stg_field_low_confidence",
                    ("structural_standardization_gap", "structure"),
                )
                self._add_signal(
                    bucket,
                    suggestion.source_table_name,
                    gap_type,
                    category,
                    "medium",
                    "stg_field_low_confidence",
                    "STG field suggestion has low confidence.",
                    affected_object=(
                        f"{suggestion.source_table_name}.{suggestion.source_field_name}"
                    ),
                )

        for suggestion in result.quality_rule_suggestions:
            if suggestion.confidence is not None and suggestion.confidence <= 0.4:
                gap_type, category = source_to_gap.get(
                    "quality_rule_low_confidence",
                    ("quality_rule_gap", "quality"),
                )
                self._add_signal(
                    bucket,
                    suggestion.source_table_name,
                    gap_type,
                    category,
                    "medium",
                    "quality_rule_low_confidence",
                    "Quality rule suggestion requires low-confidence review.",
                    affected_object=(
                        f"{suggestion.source_table_name}.{suggestion.source_field_name}"
                    ),
                )

        queue_summary = result.quality_review_queue_summary or {}
        low_confidence_count = int(queue_summary.get("low_confidence_rule_count", 0) or 0)
        manual_review_count = int(
            (result.quality_rule_review_summary or {}).get("manual_review_count", 0) or 0
        )
        if result.review_summary is not None:
            manual_review_count += int(result.review_summary.manual_review_count)
        if low_confidence_count or manual_review_count:
            gap_type, category = source_to_gap.get(
                "manual_review",
                ("review_backlog_gap", "review"),
            )
            self._add_signal(
                bucket,
                "overall",
                gap_type,
                category,
                "high" if manual_review_count else "medium",
                "manual_review" if manual_review_count else "low_confidence_review",
                (
                    f"Review backlog contains manual_review={manual_review_count}, "
                    f"low_confidence={low_confidence_count}."
                ),
                affected_object="overall",
            )

        self._add_ai_ready_signals(bucket, result)
        self._add_rag_quality_signals(bucket, result)
        self._add_text_to_sql_signals(bucket, result)

        gaps: list[GovernanceGap] = []
        for payload in bucket.values():
            source_signals = sorted(payload["source_signals"])
            reasons = list(dict.fromkeys(payload["reasons"]))
            affected_objects = sorted(payload["affected_objects"])
            signal_counts = dict(sorted(payload["signal_counts"].items()))
            severity_counts = dict(sorted(payload["severity_counts"].items()))
            signal_count = sum(signal_counts.values())
            reason_parts = []
            if affected_objects:
                reason_parts.append(
                    f"affected_objects={len(affected_objects)}"
                )
            if signal_count:
                reason_parts.append(f"signal_count={signal_count}")
            reason_parts.extend(reasons[:3])
            gaps.append(
                GovernanceGap(
                    object_type=str(payload["object_type"]),
                    object_name=str(payload["object_name"]),
                    gap_type=str(payload["gap_type"]),
                    category=str(payload["category"]),
                    severity=str(payload["severity"]),
                    source_signals=source_signals,
                    reason=" ".join(reason_parts) if reason_parts else None,
                    suggested_owner_role=self._owner_for_gap(str(payload["gap_type"])),
                    affected_objects=affected_objects,
                    signal_count=signal_count,
                    evidence_details={
                        "signal_counts": signal_counts,
                        "severity_counts": severity_counts,
                        "reason_count": len(reasons),
                        "affected_object_count": len(affected_objects),
                    },
                )
            )
        return sorted(gaps, key=lambda gap: (gap.object_name, gap.gap_type))

    @staticmethod
    def summarize(gaps: list[GovernanceGap]) -> dict[str, object]:
        """Return compact gap counts."""
        category_counts: dict[str, int] = defaultdict(int)
        severity_counts: dict[str, int] = defaultdict(int)
        for gap in gaps:
            category_counts[gap.category] += 1
            severity_counts[gap.severity] += 1
        return {
            "gap_count": len(gaps),
            "gap_category_counts": dict(category_counts),
            "gap_severity_counts": dict(severity_counts),
        }

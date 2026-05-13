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

SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}


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
    ) -> None:
        key = ("table", object_name, gap_type)
        if key not in bucket:
            bucket[key] = {
                "object_type": "table",
                "object_name": object_name,
                "gap_type": gap_type,
                "category": category,
                "severity": severity or "low",
                "source_signals": set(),
                "reasons": [],
            }
        bucket[key]["severity"] = self._stronger_severity(
            str(bucket[key]["severity"]),
            severity or "low",
        )
        bucket[key]["source_signals"].add(source_signal)
        if reason:
            bucket[key]["reasons"].append(reason)

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
            )

        gaps: list[GovernanceGap] = []
        for payload in bucket.values():
            source_signals = sorted(payload["source_signals"])
            reasons = list(dict.fromkeys(payload["reasons"]))
            gaps.append(
                GovernanceGap(
                    object_type=str(payload["object_type"]),
                    object_name=str(payload["object_name"]),
                    gap_type=str(payload["gap_type"]),
                    category=str(payload["category"]),
                    severity=str(payload["severity"]),
                    source_signals=source_signals,
                    reason=" ".join(reasons[:3]),
                    suggested_owner_role=self._owner_for_gap(str(payload["gap_type"])),
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

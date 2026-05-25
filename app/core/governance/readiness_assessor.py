"""Rule-based governance readiness assessment."""

from collections import defaultdict
from statistics import mean
from typing import Any

from app.core.models.issue import Issue
from app.core.models.readiness_score import ReadinessScore
from app.core.models.workflow_result import WorkflowResult
from app.core.rules.config_loader import get_readiness_scoring_policies_config


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def _table_from_object_name(object_name: str | None) -> str:
    text = str(object_name or "overall").strip()
    return text.split(".", 1)[0] if "." in text else text or "overall"


class ReadinessAssessor:
    """Assess governance readiness from existing workflow outputs."""

    def __init__(self, policies: dict[str, Any] | None = None) -> None:
        self.policies = policies or get_readiness_scoring_policies_config()

    def _weights(self) -> dict[str, float]:
        dimensions = self.policies.get("dimensions", {})
        if not isinstance(dimensions, dict):
            return {}
        return {
            str(name): float(payload.get("weight", 0.0))
            for name, payload in dimensions.items()
            if isinstance(payload, dict)
        }

    def _rule(self, name: str, default: float) -> float:
        rules = self.policies.get("scoring_rules", {})
        if not isinstance(rules, dict):
            return default
        return float(rules.get(name, default))

    def infer_readiness_level(self, score: float) -> str:
        thresholds = self.policies.get("thresholds", {})
        if not isinstance(thresholds, dict):
            thresholds = {}
        if score >= float(thresholds.get("ready", 0.8)):
            return "ready"
        if score >= float(thresholds.get("partially_ready", 0.5)):
            return "partially_ready"
        return "not_ready"

    @staticmethod
    def collect_table_names(result: WorkflowResult) -> list[str]:
        tables: set[str] = set()
        for issue in result.issues:
            tables.add(_table_from_object_name(issue.object_name))
        for item in result.mapping_results + result.confirmed_mapping_results:
            tables.add(item.table_name)
        for item in result.unmapped_fields:
            tables.add(item.table_name)
        for item in result.stg_field_suggestions + result.confirmed_stg_suggestions:
            tables.add(item.source_table_name)
        for item in result.quality_rule_suggestions + result.confirmed_quality_rules:
            tables.add(item.source_table_name)
        for item in result.cross_field_quality_rules:
            tables.add(item.source_table_name)
        return sorted(table for table in tables if table and table != "overall")

    @staticmethod
    def _issues_by_table(issues: list[Issue]) -> dict[str, list[Issue]]:
        grouped: dict[str, list[Issue]] = defaultdict(list)
        for issue in issues:
            grouped[_table_from_object_name(issue.object_name)].append(issue)
        return grouped

    def score_metadata_readiness(
        self,
        table_name: str,
        issues_by_table: dict[str, list[Issue]],
    ) -> float:
        score = 1.0
        for issue in issues_by_table.get(table_name, []):
            if issue.issue_type == "missing_table_description":
                score -= self._rule("missing_table_description_penalty", 0.1)
            elif issue.issue_type in {
                "missing_field_description",
                "missing_field_cn_name",
                "missing_metadata_defect",
            }:
                score -= self._rule("missing_field_description_penalty", 0.05)
            elif issue.issue_type in {
                "business_ownership_defect",
                "semantic_consistency_defect",
                "technical_object_defect",
                "ai_consumption_risk_defect",
            }:
                score -= self._rule("missing_field_description_penalty", 0.05)
        return _clamp(score)

    def score_mapping_readiness(self, table_name: str, result: WorkflowResult) -> float:
        score = 1.0
        unmapped_count = sum(1 for item in result.unmapped_fields if item.table_name == table_name)
        score -= unmapped_count * self._rule("unmapped_field_penalty", 0.08)
        low_score_count = sum(
            1
            for item in result.mapping_results
            if item.table_name == table_name and item.match_score < 0.7
        )
        score -= low_score_count * self._rule("unmapped_field_penalty", 0.08)
        return _clamp(score)

    def score_stg_readiness(
        self,
        table_name: str,
        issues_by_table: dict[str, list[Issue]],
        result: WorkflowResult,
    ) -> float:
        score = 1.0
        if result.mapping_results and not any(
            item.source_table_name == table_name for item in result.stg_field_suggestions
        ):
            score -= 0.2
        low_confidence_count = sum(
            1
            for issue in issues_by_table.get(table_name, [])
            if issue.issue_type in {"stg_field_low_confidence", "stg_table_requires_manual_review"}
        )
        score -= low_confidence_count * 0.08
        return _clamp(score)

    def score_quality_rule_readiness(self, table_name: str, result: WorkflowResult) -> float:
        suggestions = [
            item for item in result.quality_rule_suggestions if item.source_table_name == table_name
        ]
        cross_field = [
            item for item in result.cross_field_quality_rules if item.source_table_name == table_name
        ]
        confirmed = [
            item for item in result.confirmed_quality_rules if item.source_table_name == table_name
        ]
        total_recommended = len(suggestions) + len(cross_field)
        if total_recommended == 0:
            return 0.5
        coverage = len(confirmed) / max(1, total_recommended)
        score = 0.65 + min(0.30, coverage * 0.30)
        low_confidence_count = sum(
            1
            for item in suggestions
            if item.confidence is not None and item.confidence <= 0.4
        )
        low_confidence_count += sum(
            1
            for item in cross_field
            if item.confidence is not None and item.confidence <= 0.4
        )
        score -= low_confidence_count * self._rule("low_confidence_rule_penalty", 0.05)
        score += min(
            0.15,
            len(confirmed) * self._rule("confirmed_quality_rule_bonus", 0.03),
        )
        return _clamp(score)

    def score_review_completion_readiness(self, table_name: str, result: WorkflowResult) -> float:
        score = 1.0
        queue_summary = result.quality_review_queue_summary or {}
        low_confidence_count = int(queue_summary.get("low_confidence_rule_count", 0) or 0)
        score -= min(
            0.30,
            low_confidence_count * self._rule("low_confidence_rule_penalty", 0.05),
        )
        manual_review_count = int(
            (result.quality_rule_review_summary or {}).get("manual_review_count", 0) or 0
        )
        if result.review_summary is not None:
            manual_review_count += int(result.review_summary.manual_review_count)
        score -= min(
            0.40,
            manual_review_count * self._rule("manual_review_backlog_penalty", 0.08),
        )
        return _clamp(score)

    def build_table_score(
        self,
        table_name: str,
        result: WorkflowResult,
        issues_by_table: dict[str, list[Issue]],
    ) -> ReadinessScore:
        dimension_scores = {
            "metadata_readiness": self.score_metadata_readiness(table_name, issues_by_table),
            "mapping_readiness": self.score_mapping_readiness(table_name, result),
            "stg_readiness": self.score_stg_readiness(table_name, issues_by_table, result),
            "quality_rule_readiness": self.score_quality_rule_readiness(table_name, result),
            "review_completion_readiness": self.score_review_completion_readiness(
                table_name,
                result,
            ),
        }
        weights = self._weights()
        weight_total = sum(weights.get(name, 0.0) for name in dimension_scores) or 1.0
        overall_score = _clamp(
            sum(dimension_scores[name] * weights.get(name, 0.0) for name in dimension_scores)
            / weight_total
        )
        readiness_level = self.infer_readiness_level(overall_score)
        return ReadinessScore(
            object_type="table",
            object_name=table_name,
            overall_score=overall_score,
            readiness_level=readiness_level,
            dimension_scores=dimension_scores,
            summary=(
                f"{table_name} readiness is {readiness_level} with score "
                f"{overall_score:.2f}."
            ),
        )

    def assess(self, result: WorkflowResult) -> list[ReadinessScore]:
        """Build table-level readiness scores plus an overall score."""
        table_names = self.collect_table_names(result)
        issues_by_table = self._issues_by_table(result.issues)
        table_scores = [
            self.build_table_score(table_name, result, issues_by_table)
            for table_name in table_names
        ]
        if not table_scores:
            return [
                ReadinessScore(
                    object_type="overall",
                    object_name="overall",
                    overall_score=0.0,
                    readiness_level="not_ready",
                    dimension_scores={},
                    summary="No governance outputs were available for readiness scoring.",
                )
            ]

        dimension_names = list(table_scores[0].dimension_scores.keys())
        overall_dimensions = {
            name: _clamp(mean(float(score.dimension_scores.get(name, 0.0)) for score in table_scores))
            for name in dimension_names
        }
        overall_score = _clamp(mean(score.overall_score for score in table_scores))
        overall = ReadinessScore(
            object_type="overall",
            object_name="overall",
            overall_score=overall_score,
            readiness_level=self.infer_readiness_level(overall_score),
            dimension_scores=overall_dimensions,
            summary=(
                f"Overall governance readiness is {self.infer_readiness_level(overall_score)} "
                f"across {len(table_scores)} tables."
            ),
        )
        return table_scores + [overall]

    @staticmethod
    def summarize(readiness_scores: list[ReadinessScore]) -> dict[str, object]:
        """Return a compact readiness summary."""
        level_counts: dict[str, int] = {}
        for score in readiness_scores:
            level_counts[score.readiness_level] = level_counts.get(score.readiness_level, 0) + 1
        overall = next(
            (score for score in readiness_scores if score.object_type == "overall"),
            None,
        )
        return {
            "readiness_score_count": len(readiness_scores),
            "readiness_level_counts": level_counts,
            "overall_score": overall.overall_score if overall else None,
            "overall_readiness_level": overall.readiness_level if overall else None,
        }

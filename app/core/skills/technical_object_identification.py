"""Rule-based v1 skill for technical object identification."""

from collections import defaultdict

from pydantic import BaseModel, Field

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import (
    get_issue_severity,
    get_lifecycle_keywords_config,
    get_technical_keywords_config,
)
from app.core.skills.base_skill import BaseSkill

TEXT_WEIGHTS = {
    "table_name": 3,
    "table_name_cn": 2,
    "table_description": 1,
}


class TechnicalObjectIdentificationInput(BaseModel):
    """Input schema for technical object identification."""

    tables: list[TableMeta] = Field(default_factory=list)


class TechnicalObjectIdentificationOutput(BaseModel):
    """Output schema for technical object identification."""

    identified_objects: dict[str, str] = Field(default_factory=dict)
    object_scores: dict[str, dict[str, int]] = Field(default_factory=dict)
    object_confidence: dict[str, float] = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


class TechnicalObjectIdentificationSkill(BaseSkill):
    """Identify technical tables using configured keyword rules."""

    skill_name = "technical_object_identification"
    version = "0.2.0"
    description = "Rule-based v1 technical object detection using configured keywords."

    @staticmethod
    def _collect_texts(table: TableMeta) -> dict[str, str]:
        return {
            "table_name": (table.table_name or "").lower(),
            "table_name_cn": (table.table_name_cn or "").lower(),
            "table_description": (table.table_description or "").lower(),
        }

    @staticmethod
    def _record_matches(
        texts: dict[str, str],
        category_keywords: dict[str, list[str]],
    ) -> tuple[dict[str, int], dict[str, list[str]]]:
        scores: dict[str, int] = defaultdict(int)
        evidence: dict[str, list[str]] = defaultdict(list)

        for category, keywords in category_keywords.items():
            for keyword in keywords:
                normalized_keyword = keyword.lower()
                for source_name, source_text in texts.items():
                    if normalized_keyword and normalized_keyword in source_text:
                        scores[category] += TEXT_WEIGHTS.get(source_name, 1)
                        evidence[category].append(
                            f"matched '{keyword}' in {source_name}"
                        )

        return dict(scores), dict(evidence)

    @staticmethod
    def _merge_category_keywords() -> dict[str, list[str]]:
        technical_keywords = get_technical_keywords_config()
        lifecycle_keywords = get_lifecycle_keywords_config().get("category_hints", {})
        merged: dict[str, list[str]] = {}

        for category, keywords in technical_keywords.items():
            merged[category] = list(
                dict.fromkeys(list(keywords) + list(lifecycle_keywords.get(category, [])))
            )

        for category, keywords in lifecycle_keywords.items():
            merged.setdefault(category, list(keywords))

        return merged

    @staticmethod
    def _calculate_confidence(top_score: int, runner_up_score: int) -> float:
        if top_score <= 0:
            return 0.0

        raw_confidence = top_score / 6
        if top_score - runner_up_score >= 2:
            raw_confidence += 0.1
        elif top_score == runner_up_score:
            raw_confidence -= 0.1

        return round(max(0.1, min(raw_confidence, 0.95)), 2)

    @staticmethod
    def _build_issue(
        issue_id: str,
        object_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
    ) -> Issue:
        return Issue(
            issue_id=issue_id,
            object_type="table",
            object_name=object_name,
            issue_type=issue_type,
            severity=get_issue_severity(issue_type),
            evidence=evidence,
            suggestion=suggestion,
            confidence=confidence,
        )

    def run(
        self, payload: TechnicalObjectIdentificationInput
    ) -> TechnicalObjectIdentificationOutput:
        """Run rule-based technical object detection on table metadata."""
        category_keywords = self._merge_category_keywords()
        identified_objects: dict[str, str] = {}
        object_scores: dict[str, dict[str, int]] = {}
        object_confidence: dict[str, float] = {}
        issues: list[Issue] = []

        for table_index, table in enumerate(payload.tables, start=1):
            texts = self._collect_texts(table)
            scores, category_evidence = self._record_matches(texts, category_keywords)
            table_name = table.table_name or f"table_{table_index}"
            sorted_categories = sorted(
                scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            if not sorted_categories or sorted_categories[0][1] <= 0:
                identified_objects[table_name] = "business_table"
                object_scores[table_name] = {}
                object_confidence[table_name] = 0.0
                continue

            top_category, top_score = sorted_categories[0]
            runner_up_score = sorted_categories[1][1] if len(sorted_categories) > 1 else 0
            confidence = self._calculate_confidence(top_score, runner_up_score)
            evidence = list(category_evidence.get(top_category, []))

            if runner_up_score and top_score - runner_up_score <= 1:
                runner_up_category = sorted_categories[1][0]
                evidence.append(
                    f"ambiguous classification: {runner_up_category} also scored {runner_up_score}"
                )

            identified_objects[table_name] = top_category
            object_scores[table_name] = scores
            object_confidence[table_name] = confidence

            issues.append(
                self._build_issue(
                    issue_id=f"{self.skill_name}-detected-{table_index}",
                    object_name=table_name,
                    issue_type="technical_object_detected",
                    evidence=evidence
                    + [
                        f"predicted object type={top_category}",
                        f"score={top_score}",
                    ],
                    suggestion=(
                        "Review whether this table belongs in the business metadata "
                        "catalog or should be isolated as a technical asset."
                    ),
                    confidence=confidence,
                )
            )

            if top_score >= 4 or confidence >= 0.65:
                issues.append(
                    self._build_issue(
                        issue_id=f"{self.skill_name}-risk-{table_index}",
                        object_name=table_name,
                        issue_type="technical_purity_risk",
                        evidence=[
                            f"technical object classification={top_category}",
                            f"confidence={confidence}",
                        ]
                        + evidence,
                        suggestion=(
                            "Assess whether the table should remain in the business "
                            "catalog or be documented in a technical-only domain."
                        ),
                        confidence=confidence,
                    )
                )

        detected_count = sum(
            1 for object_type in identified_objects.values() if object_type != "business_table"
        )

        # TODO: refine scoring weights and category ambiguity handling with richer metadata cues.
        return TechnicalObjectIdentificationOutput(
            identified_objects=identified_objects,
            object_scores=object_scores,
            object_confidence=object_confidence,
            issues=issues,
            summary=(
                f"Scanned {len(payload.tables)} tables and flagged {detected_count} "
                f"non-business technical objects."
            ),
        )

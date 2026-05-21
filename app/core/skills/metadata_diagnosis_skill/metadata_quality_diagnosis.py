"""Rule-based v1 skill for diagnosis-layer defect aggregation."""

from collections import defaultdict

from pydantic import BaseModel, Field

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import get_issue_severity
from app.core.skills.base_skill import BaseSkill

DEFECT_SEVERITY = {
    "business_ownership_defect": "high",
    "semantic_description_defect": "medium",
    "technical_purity_defect": "medium",
    "naming_standard_defect": "low",
}

ISSUE_TYPE_TO_DEFECT = {
    "naming_contains_space": "naming_standard_defect",
    "naming_contains_repeated_underscore": "naming_standard_defect",
    "naming_contains_uppercase": "naming_standard_defect",
    "naming_contains_disallowed_prefix": "naming_standard_defect",
    "naming_not_snake_case": "naming_standard_defect",
    "naming_too_long": "naming_standard_defect",
    "naming_suspected_spelling_error": "naming_standard_defect",
    "missing_table_description": "semantic_description_defect",
    "missing_field_description": "semantic_description_defect",
    "suspicious_short_description": "semantic_description_defect",
    "placeholder_description": "semantic_description_defect",
    "description_same_as_name": "semantic_description_defect",
    "missing_table_cn_name": "business_ownership_defect",
    "missing_field_cn_name": "business_ownership_defect",
    "ambiguous_business_identity": "business_ownership_defect",
    "weak_business_semantics": "business_ownership_defect",
    "technical_object_detected": "technical_purity_defect",
    "technical_purity_risk": "technical_purity_defect",
    "missing_table_name": "business_ownership_defect",
    "missing_field_name": "business_ownership_defect",
}

DEFECT_SUGGESTIONS = {
    "naming_standard_defect": "Standardize identifiers to snake_case and remove unnecessary technical prefixes.",
    "semantic_description_defect": "Complete business descriptions and replace placeholder or low-quality text.",
    "business_ownership_defect": "Add Chinese labels, clarify business meaning, and complete ownership-related metadata.",
    "technical_purity_defect": "Consider isolating technical tables from the business metadata catalog or labeling them explicitly.",
}


class MetadataQualityDiagnosisInput(BaseModel):
    """Input schema for quality diagnosis."""

    tables: list[TableMeta] = Field(default_factory=list)
    upstream_issues: list[Issue] = Field(default_factory=list)


class MetadataQualityDiagnosisOutput(BaseModel):
    """Output schema for quality diagnosis."""

    defect_summary: dict[str, int] = Field(default_factory=dict)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


class MetadataQualityDiagnosisSkill(BaseSkill):
    """Aggregate raw issues into governance-oriented defect issues."""

    skill_name = "metadata_quality_diagnosis"
    version = "0.2.0"
    description = "Rule-based v1 diagnosis that groups raw issues into defect categories."

    @staticmethod
    def map_issue_type_to_defect(issue_type: str) -> str | None:
        """Map a raw issue type to a diagnosis defect type."""
        return ISSUE_TYPE_TO_DEFECT.get(issue_type)

    @staticmethod
    def _parent_object_name(issue: Issue) -> str:
        if issue.object_type == "field" and "." in issue.object_name:
            return issue.object_name.split(".", 1)[0]
        return issue.object_name

    @classmethod
    def group_issues_by_object(
        cls, issues: list[Issue]
    ) -> dict[str, dict[str, list[Issue]]]:
        """Group issues by top-level object and mapped defect type."""
        grouped: dict[str, dict[str, list[Issue]]] = defaultdict(lambda: defaultdict(list))

        for issue in issues:
            defect_type = cls.map_issue_type_to_defect(issue.issue_type)
            if defect_type is None:
                continue
            grouped[cls._parent_object_name(issue)][defect_type].append(issue)

        return {object_name: dict(defect_groups) for object_name, defect_groups in grouped.items()}

    @staticmethod
    def build_diagnosis_issue(
        object_name: str, defect_type: str, source_issues: list[Issue]
    ) -> Issue:
        """Build one diagnosis issue from grouped source issues."""
        safe_object_name = (
            object_name.replace(" ", "_").replace(".", "_").replace("/", "_")
        )
        unique_issue_types = sorted({issue.issue_type for issue in source_issues})
        evidence = [
            f"aggregated_from_issue_types={', '.join(unique_issue_types)}",
            f"supporting_issue_count={len(source_issues)}",
        ]
        if any(issue.object_type == "field" for issue in source_issues):
            affected_fields = sorted(
                issue.object_name for issue in source_issues if issue.object_type == "field"
            )
            evidence.append(f"affected_fields={', '.join(affected_fields[:5])}")

        confidence = round(min(0.95, 0.45 + len(source_issues) * 0.1), 2)
        return Issue(
            issue_id=f"metadata_quality_diagnosis-{safe_object_name}-{defect_type}",
            object_type="diagnosis",
            object_name=object_name,
            issue_type=defect_type,
            severity=get_issue_severity(defect_type, DEFECT_SEVERITY.get(defect_type, "low")),
            evidence=evidence,
            suggestion=DEFECT_SUGGESTIONS.get(defect_type, "Review grouped governance findings."),
            confidence=confidence,
        )

    def run(self, payload: MetadataQualityDiagnosisInput) -> MetadataQualityDiagnosisOutput:
        """Aggregate upstream issues into diagnosis-layer defect issues."""
        grouped_issues = self.group_issues_by_object(payload.upstream_issues)
        diagnosis_issues: list[Issue] = []
        defect_summary: dict[str, int] = defaultdict(int)

        for object_name, defect_groups in grouped_issues.items():
            for defect_type, source_issues in defect_groups.items():
                diagnosis_issue = self.build_diagnosis_issue(
                    object_name=object_name,
                    defect_type=defect_type,
                    source_issues=source_issues,
                )
                diagnosis_issues.append(diagnosis_issue)
                defect_summary[defect_type] += 1

        # TODO: extend diagnosis with cross-table ownership inference and domain-level rollups.
        return MetadataQualityDiagnosisOutput(
            defect_summary=dict(defect_summary),
            issues=diagnosis_issues,
            summary=(
                f"Aggregated {len(payload.upstream_issues)} raw issues into "
                f"{len(diagnosis_issues)} diagnosis issues across {len(defect_summary)} defect types."
            ),
        )

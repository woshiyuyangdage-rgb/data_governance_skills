"""Structured rule-based metadata diagnosis skill."""

from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.models.field_meta import FieldMeta
from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import get_issue_severity
from app.core.skills.base_skill import BaseSkill
from app.core.skills.metadata_diagnosis_skill.metadata_diagnosis_finding import (
    MetadataDiagnosisFinding,
)

DEFECT_SEVERITY = {
    "missing_metadata_defect": "high",
    "naming_standard_defect": "low",
    "semantic_consistency_defect": "medium",
    "business_ownership_defect": "high",
    "technical_object_defect": "medium",
    "ai_consumption_risk_defect": "medium",
}


class MetadataQualityDiagnosisInput(BaseModel):
    """Input schema for quality diagnosis."""

    tables: list[TableMeta] = Field(default_factory=list)
    upstream_issues: list[Issue] = Field(default_factory=list)


class MetadataQualityDiagnosisOutput(BaseModel):
    """Output schema for quality diagnosis."""

    defect_summary: dict[str, int] = Field(default_factory=dict)
    findings: list[MetadataDiagnosisFinding] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


@dataclass(frozen=True)
class _DiagnosisProfile:
    table: TableMeta
    domain_pack_name: str | None


class MetadataQualityDiagnosisSkill(BaseSkill):
    """Aggregate raw issues into structured governance diagnosis findings."""

    skill_name = "metadata_quality_diagnosis"
    version = "0.3.0"
    description = "Rule-based metadata diagnosis that produces structured AI-ready findings."

    @staticmethod
    def map_issue_type_to_defect(issue_type: str) -> str | None:
        """Map a raw issue type to a diagnosis defect type."""
        mapping = {
            "missing_table_name": "missing_metadata_defect",
            "missing_table_cn_name": "missing_metadata_defect",
            "missing_table_description": "missing_metadata_defect",
            "missing_field_name": "missing_metadata_defect",
            "missing_field_cn_name": "missing_metadata_defect",
            "missing_field_description": "missing_metadata_defect",
            "naming_contains_space": "naming_standard_defect",
            "naming_contains_repeated_underscore": "naming_standard_defect",
            "naming_contains_uppercase": "naming_standard_defect",
            "naming_contains_disallowed_prefix": "naming_standard_defect",
            "naming_not_snake_case": "naming_standard_defect",
            "naming_too_long": "naming_standard_defect",
            "naming_suspected_spelling_error": "naming_standard_defect",
            "description_same_as_name": "semantic_consistency_defect",
            "placeholder_description": "semantic_consistency_defect",
            "suspicious_short_description": "semantic_consistency_defect",
            "technical_object_detected": "technical_object_defect",
            "technical_purity_risk": "technical_object_defect",
            "business_domain_missing": "business_ownership_defect",
            "owner_role_missing": "business_ownership_defect",
            "lifecycle_status_missing": "business_ownership_defect",
            "standard_mapping_missing": "semantic_consistency_defect",
            "standard_mapping_low_confidence": "semantic_consistency_defect",
            "standard_mapping_suspected_wrong": "semantic_consistency_defect",
            "ai_consumption_risk": "ai_consumption_risk_defect",
            "sensitive_field_unlabeled": "ai_consumption_risk_defect",
        }
        return mapping.get(issue_type)

    @staticmethod
    def _parent_object_name(issue: Issue) -> str:
        if issue.object_type == "field" and "." in issue.object_name:
            return issue.object_name.split(".", 1)[0]
        return issue.object_name

    @staticmethod
    def _issue_priority(defect_type: str) -> str:
        return {
            "missing_metadata_defect": "priority_governance",
            "business_ownership_defect": "priority_governance",
            "semantic_consistency_defect": "key_tracking",
            "technical_object_defect": "key_tracking",
            "ai_consumption_risk_defect": "priority_governance",
            "naming_standard_defect": "continuous_observation",
        }.get(defect_type, "continuous_observation")

    @staticmethod
    def _impact_scope(defect_type: str, object_type: str) -> str:
        if defect_type == "ai_consumption_risk_defect":
            return "text-to-sql/rag/assistant"
        if object_type == "field":
            return "field-level consumption"
        return "table-level consumption"

    @staticmethod
    def _ai_risk(defect_type: str) -> str | None:
        return {
            "missing_metadata_defect": "models may lack enough context to interpret the asset",
            "semantic_consistency_defect": "retrieval and answer generation may misread the business meaning",
            "business_ownership_defect": "ownership ambiguity can lead to wrong governance routing",
            "technical_object_defect": "technical assets may pollute the business catalog",
            "ai_consumption_risk_defect": "AI applications may misinterpret or over-trust the asset",
            "naming_standard_defect": "naming noise can reduce retrieval and matching quality",
        }.get(defect_type)

    @classmethod
    def _profile_for_table(cls, table: TableMeta) -> _DiagnosisProfile:
        domain_pack_name = None
        if table.business_domain or table.system_name or table.table_name:
            match = DomainPackMatcher().match_domain_pack_from_tables([table])
            if not match.fallback_used:
                domain_pack_name = match.matched_pack_name
        return _DiagnosisProfile(table=table, domain_pack_name=domain_pack_name)

    @staticmethod
    def _build_issue(
        object_type: str,
        object_name: str,
        issue_type: str,
        severity: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
        system_name: str | None = None,
        business_domain: str | None = None,
    ) -> Issue:
        return Issue(
            issue_id=f"metadata_quality_diagnosis-{object_type}-{object_name}-{issue_type}".replace(
                " ", "_"
            ).replace(".", "_").replace("/", "_"),
            object_type=object_type,
            object_name=object_name,
            issue_type=issue_type,
            severity=severity,
            evidence=evidence,
            suggestion=suggestion,
            confidence=confidence,
            system_name=system_name,
            business_domain=business_domain,
            impact_scope=MetadataQualityDiagnosisSkill._impact_scope(issue_type, object_type),
            ai_risk=MetadataQualityDiagnosisSkill._ai_risk(issue_type),
            recommended_priority=MetadataQualityDiagnosisSkill._issue_priority(issue_type),
            requires_manual_review=severity in {"medium", "high"},
            evidence_details={"source": "structured_metadata_diagnosis"},
        )

    @staticmethod
    def _finding(
        *,
        finding_id: str,
        object_type: str,
        object_name: str,
        issue_type: str,
        severity: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
        system_name: str | None,
        business_domain: str | None,
        impact_scope: str | None,
        ai_risk: str | None,
        requires_manual_review: bool,
        evidence_details: dict[str, object] | None = None,
    ) -> MetadataDiagnosisFinding:
        return MetadataDiagnosisFinding(
            finding_id=finding_id,
            object_type=object_type,
            object_name=object_name,
            system_name=system_name,
            business_domain=business_domain,
            issue_type=issue_type,
            severity=severity,
            impact_scope=impact_scope,
            ai_risk=ai_risk,
            evidence=evidence,
            suggestion=suggestion,
            requires_manual_review=requires_manual_review,
            recommended_priority=MetadataQualityDiagnosisSkill._issue_priority(issue_type),
            confidence=confidence,
            evidence_details=evidence_details or {},
        )

    @staticmethod
    def _table_missing_metadata(table: TableMeta) -> list[MetadataDiagnosisFinding]:
        findings: list[MetadataDiagnosisFinding] = []
        if not table.table_description:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-table-description-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="missing_metadata_defect",
                    severity=get_issue_severity("missing_table_description", DEFECT_SEVERITY["missing_metadata_defect"]),
                    evidence=["table_description is blank"],
                    suggestion="补充表级业务说明，说明这张表在业务流程中的角色。",
                    confidence=0.96,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="table-level consumption",
                    ai_risk="Text-to-SQL and RAG may not understand the table purpose.",
                    requires_manual_review=False,
                )
            )
        if not table.business_domain:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-business-domain-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="business_ownership_defect",
                    severity=DEFECT_SEVERITY["business_ownership_defect"],
                    evidence=["business_domain is blank"],
                    suggestion="补充业务域归属，方便治理路由和检索过滤。",
                    confidence=0.9,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="catalog governance",
                    ai_risk="Ambiguous domain boundaries reduce governance routing quality.",
                    requires_manual_review=True,
                )
            )
        if not table.lifecycle_status:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-lifecycle-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="business_ownership_defect",
                    severity=DEFECT_SEVERITY["business_ownership_defect"],
                    evidence=["lifecycle_status is blank"],
                    suggestion="补充生命周期标记，区分正式、临时、历史或归档资产。",
                    confidence=0.88,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="catalog lifecycle",
                    ai_risk="Lifecycle ambiguity may pollute retrieval and asset catalogs.",
                    requires_manual_review=True,
                )
            )
        if table.sensitivity_label is None and any(
            getattr(field, "is_sensitive", None) for field in table.fields
        ):
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-sensitivity-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="ai_consumption_risk_defect",
                    severity=DEFECT_SEVERITY["ai_consumption_risk_defect"],
                    evidence=["fields contain sensitive indicators but sensitivity_label is blank"],
                    suggestion="补充敏感级别标签，避免 AI 应用误用敏感字段。",
                    confidence=0.92,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="ai authorization",
                    ai_risk="Sensitive data may be consumed without enough guardrails.",
                    requires_manual_review=True,
                )
            )
        return findings

    @staticmethod
    def _field_findings(table: TableMeta, field: FieldMeta) -> list[MetadataDiagnosisFinding]:
        findings: list[MetadataDiagnosisFinding] = []
        field_name = field.field_name
        field_key = f"{table.table_name}.{field_name}"
        if not field.field_description:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-field-description-{field_key}",
                    object_type="field",
                    object_name=field_key,
                    issue_type="missing_metadata_defect",
                    severity=DEFECT_SEVERITY["missing_metadata_defect"],
                    evidence=["field_description is blank"],
                    suggestion="补充字段描述，说明它的业务含义、口径和取值范围。",
                    confidence=0.95,
                    system_name=table.system_name,
                    business_domain=field.business_domain or table.business_domain,
                    impact_scope="field-level consumption",
                    ai_risk="Models may not understand the exact field meaning.",
                    requires_manual_review=False,
                )
            )
        if not field.field_name_cn:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-field-cn-{field_key}",
                    object_type="field",
                    object_name=field_key,
                    issue_type="business_ownership_defect",
                    severity=DEFECT_SEVERITY["business_ownership_defect"],
                    evidence=["field_name_cn is blank"],
                    suggestion="补充字段中文名，帮助业务人员和模型理解。",
                    confidence=0.9,
                    system_name=table.system_name,
                    business_domain=field.business_domain or table.business_domain,
                    impact_scope="field-level consumption",
                    ai_risk="Missing display labels hurt explainability and reviewability.",
                    requires_manual_review=True,
                )
            )
        if field.standard_code is None and field.standard_name is None:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"missing-standard-{field_key}",
                    object_type="field",
                    object_name=field_key,
                    issue_type="semantic_consistency_defect",
                    severity=DEFECT_SEVERITY["semantic_consistency_defect"],
                    evidence=["no standard mapping bound to field"],
                    suggestion="补充标准映射关系，提升统一语义和可复用性。",
                    confidence=0.86,
                    system_name=table.system_name,
                    business_domain=field.business_domain or table.business_domain,
                    impact_scope="standard mapping",
                    ai_risk="RAG and data assistants may infer the wrong business concept.",
                    requires_manual_review=True,
                )
            )
        if field.is_sensitive and not field.catalog_path:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"sensitive-field-unlabeled-{field_key}",
                    object_type="field",
                    object_name=field_key,
                    issue_type="ai_consumption_risk_defect",
                    severity=DEFECT_SEVERITY["ai_consumption_risk_defect"],
                    evidence=["sensitive field lacks catalog path or explicit protection context"],
                    suggestion="补充目录和安全标签，避免 AI 消费时越权。",
                    confidence=0.9,
                    system_name=table.system_name,
                    business_domain=field.business_domain or table.business_domain,
                    impact_scope="ai authorization",
                    ai_risk="Sensitive field could be surfaced without proper context.",
                    requires_manual_review=True,
                )
            )
        return findings

    @staticmethod
    def _technical_table_findings(profile: _DiagnosisProfile) -> list[MetadataDiagnosisFinding]:
        table = profile.table
        findings: list[MetadataDiagnosisFinding] = []
        name = table.table_name.lower()
        if any(token in name for token in ("tmp", "temp", "bak", "old", "his", "test")):
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"technical-table-name-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="technical_object_defect",
                    severity=DEFECT_SEVERITY["technical_object_defect"],
                    evidence=[f"technical token found in table_name={table.table_name}"],
                    suggestion="将技术表从业务目录中隔离，或显式标记为技术资产。",
                    confidence=0.93,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="catalog hygiene",
                    ai_risk="Technical tables may pollute retrieval and selection.",
                    requires_manual_review=True,
                )
            )
        if profile.domain_pack_name is None and table.business_domain:
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"domain-pack-gap-{table.table_name}",
                    object_type="table",
                    object_name=table.table_name,
                    issue_type="business_ownership_defect",
                    severity=DEFECT_SEVERITY["business_ownership_defect"],
                    evidence=[f"no domain governance pack matched business_domain={table.business_domain}"],
                    suggestion="补充领域治理包或调整业务域关键词，使治理路由更稳定。",
                    confidence=0.72,
                    system_name=table.system_name,
                    business_domain=table.business_domain,
                    impact_scope="domain governance",
                    ai_risk="Domain routing may be ambiguous for this asset.",
                    requires_manual_review=True,
                )
            )
        return findings

    @classmethod
    def _findings_to_issues(cls, findings: list[MetadataDiagnosisFinding]) -> list[Issue]:
        issues: list[Issue] = []
        for finding in findings:
            issues.append(
                Issue(
                    issue_id=finding.finding_id,
                    object_type=finding.object_type,
                    object_name=finding.object_name,
                    issue_type=finding.issue_type,
                    severity=finding.severity,
                    evidence=list(finding.evidence),
                    suggestion=finding.suggestion,
                    confidence=finding.confidence,
                    system_name=finding.system_name,
                    business_domain=finding.business_domain,
                    impact_scope=finding.impact_scope,
                    ai_risk=finding.ai_risk,
                    recommended_priority=finding.recommended_priority,
                    requires_manual_review=finding.requires_manual_review,
                    evidence_details=finding.evidence_details,
                )
            )
        return issues

    def run(self, payload: MetadataQualityDiagnosisInput) -> MetadataQualityDiagnosisOutput:
        """Aggregate upstream issues and generate structured diagnosis findings."""
        findings: list[MetadataDiagnosisFinding] = []
        defect_summary: dict[str, int] = defaultdict(int)

        upstream_defects: dict[str, list[Issue]] = defaultdict(list)
        for issue in payload.upstream_issues:
            defect_type = self.map_issue_type_to_defect(issue.issue_type)
            if defect_type is None:
                continue
            upstream_defects[defect_type].append(issue)

        for table in payload.tables:
            profile = self._profile_for_table(table)
            table_findings = []
            table_findings.extend(self._table_missing_metadata(table))
            table_findings.extend(self._technical_table_findings(profile))
            for field in table.fields:
                table_findings.extend(self._field_findings(table, field))
            findings.extend(table_findings)

        for defect_type, source_issues in upstream_defects.items():
            root_object = self._parent_object_name(source_issues[0]) if source_issues else "overall"
            findings.append(
                MetadataQualityDiagnosisSkill._finding(
                    finding_id=f"aggregated-{root_object}-{defect_type}",
                    object_type="diagnosis",
                    object_name=root_object,
                    issue_type=defect_type,
                    severity=get_issue_severity(defect_type, DEFECT_SEVERITY.get(defect_type, "low")),
                    evidence=[
                        f"aggregated_from_issue_types={', '.join(sorted({issue.issue_type for issue in source_issues}))}",
                        f"supporting_issue_count={len(source_issues)}",
                    ],
                    suggestion="根据上游问题单进行统一治理或人工复核。",
                    confidence=round(min(0.95, 0.55 + len(source_issues) * 0.08), 2),
                    system_name=source_issues[0].system_name if source_issues else None,
                    business_domain=source_issues[0].business_domain if source_issues else None,
                    impact_scope="diagnosis aggregation",
                    ai_risk=MetadataQualityDiagnosisSkill._ai_risk(defect_type),
                    requires_manual_review=True,
                )
            )

        for finding in findings:
            defect_summary[finding.issue_type] += 1

        issues = self._findings_to_issues(findings)
        return MetadataQualityDiagnosisOutput(
            defect_summary=dict(defect_summary),
            findings=findings,
            issues=issues,
            summary=(
                f"Generated {len(findings)} structured findings from {len(payload.tables)} tables "
                f"and {len(payload.upstream_issues)} upstream issues."
            ),
        )

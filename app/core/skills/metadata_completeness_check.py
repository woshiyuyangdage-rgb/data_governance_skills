"""Rule-based v1 skill for metadata completeness and description quality."""

from pydantic import BaseModel, Field

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta
from app.core.rules.config_loader import get_issue_severity
from app.core.skills.base_skill import BaseSkill

PLACEHOLDER_TEXTS = {
    "test",
    "tmp",
    "none",
    "null",
    "n/a",
    "na",
    "无",
    "暂无",
}


class MetadataCompletenessInput(BaseModel):
    """Input schema for metadata completeness checks."""

    tables: list[TableMeta] = Field(default_factory=list)


class MetadataCompletenessOutput(BaseModel):
    """Output schema for metadata completeness checks."""

    total_tables: int = 0
    total_fields: int = 0
    table_description_coverage: float = 0.0
    field_cn_name_coverage: float = 0.0
    field_description_coverage: float = 0.0
    missing_description_tables: list[str] = Field(default_factory=list)
    missing_cn_name_fields: list[str] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    summary: str = ""


class MetadataCompletenessCheckSkill(BaseSkill):
    """Check completeness and simple description quality for metadata assets."""

    skill_name = "metadata_completeness_check"
    version = "0.2.0"
    description = "Rule-based v1 checks for required metadata and description quality."

    @staticmethod
    def is_blank_text(text: str | None) -> bool:
        """Return whether text is blank after trimming."""
        return text is None or not text.strip()

    @classmethod
    def is_placeholder_text(cls, text: str | None) -> bool:
        """Return whether text looks like a placeholder value."""
        if cls.is_blank_text(text):
            return False
        normalized = text.strip().lower()
        return normalized in PLACEHOLDER_TEXTS

    @classmethod
    def is_low_quality_description(cls, name: str, description: str | None) -> bool:
        """Return whether description quality is suspicious."""
        return bool(cls.collect_description_quality_issues(name, description))

    @classmethod
    def collect_description_quality_issues(
        cls, name: str, description: str | None
    ) -> list[tuple[str, str]]:
        """Return issue types and evidence for low-quality descriptions."""
        if cls.is_blank_text(description):
            return []

        normalized_description = description.strip()
        normalized_name = name.strip()
        reasons: list[tuple[str, str]] = []

        if len(normalized_description.replace(" ", "")) < 4:
            reasons.append(
                (
                    "suspicious_short_description",
                    f"description is shorter than 4 non-space characters: '{normalized_description}'",
                )
            )
        if normalized_description.casefold() == normalized_name.casefold():
            reasons.append(
                (
                    "description_same_as_name",
                    f"description is identical to name: '{normalized_description}'",
                )
            )
        if cls.is_placeholder_text(normalized_description):
            reasons.append(
                (
                    "placeholder_description",
                    f"description uses placeholder text: '{normalized_description}'",
                )
            )

        return reasons

    @staticmethod
    def _build_issue(
        issue_id: str,
        object_type: str,
        object_name: str,
        issue_type: str,
        evidence: list[str],
        suggestion: str,
        confidence: float,
    ) -> Issue:
        """Create a normalized issue object with configured severity."""
        return Issue(
            issue_id=issue_id,
            object_type=object_type,
            object_name=object_name,
            issue_type=issue_type,
            severity=get_issue_severity(issue_type),
            evidence=evidence,
            suggestion=suggestion,
            confidence=confidence,
        )

    def run(self, payload: MetadataCompletenessInput) -> MetadataCompletenessOutput:
        """Run rule-based v1 completeness and description-quality checks."""
        total_fields = 0
        tables_with_description = 0
        fields_with_cn_name = 0
        fields_with_description = 0
        missing_description_tables: list[str] = []
        missing_cn_name_fields: list[str] = []
        issues: list[Issue] = []

        for table_index, table in enumerate(payload.tables, start=1):
            table_name = table.table_name or f"table_{table_index}"
            if not self.is_blank_text(table.table_description):
                tables_with_description += 1

            if self.is_blank_text(table.table_name):
                issues.append(
                    self._build_issue(
                        issue_id=f"{self.skill_name}-table-name-{table_index}",
                        object_type="table",
                        object_name=table_name,
                        issue_type="missing_table_name",
                        evidence=["table_name is blank"],
                        suggestion="Provide a non-empty technical table name.",
                        confidence=0.98,
                    )
                )

            if self.is_blank_text(table.table_name_cn):
                issues.append(
                    self._build_issue(
                        issue_id=f"{self.skill_name}-table-cn-{table_index}",
                        object_type="table",
                        object_name=table_name,
                        issue_type="missing_table_cn_name",
                        evidence=["table_name_cn is blank"],
                        suggestion="Add a Chinese business label for the table.",
                        confidence=0.95,
                    )
                )

            if self.is_blank_text(table.table_description):
                missing_description_tables.append(table_name)
                issues.append(
                    self._build_issue(
                        issue_id=f"{self.skill_name}-table-desc-{table_index}",
                        object_type="table",
                        object_name=table_name,
                        issue_type="missing_table_description",
                        evidence=["table_description is blank"],
                        suggestion="Add a concise business-oriented table description.",
                        confidence=0.95,
                    )
                )
            else:
                for quality_index, (issue_type, evidence_text) in enumerate(
                    self.collect_description_quality_issues(
                        table.table_name, table.table_description
                    ),
                    start=1,
                ):
                    issues.append(
                        self._build_issue(
                            issue_id=f"{self.skill_name}-table-quality-{table_index}-{quality_index}",
                            object_type="table",
                            object_name=table_name,
                            issue_type=issue_type,
                            evidence=[evidence_text],
                            suggestion="Improve the table description to explain business meaning and usage.",
                            confidence=0.78,
                        )
                    )

            for field_index, field in enumerate(table.fields, start=1):
                total_fields += 1
                field_name = field.field_name or f"field_{field_index}"
                field_key = f"{table_name}.{field_name}"

                if not self.is_blank_text(field.field_name_cn):
                    fields_with_cn_name += 1
                if not self.is_blank_text(field.field_description):
                    fields_with_description += 1

                if self.is_blank_text(field.field_name):
                    issues.append(
                        self._build_issue(
                            issue_id=f"{self.skill_name}-field-name-{table_index}-{field_index}",
                            object_type="field",
                            object_name=field_key,
                            issue_type="missing_field_name",
                            evidence=["field_name is blank"],
                            suggestion="Provide a non-empty technical field name.",
                            confidence=0.98,
                        )
                    )

                if self.is_blank_text(field.field_name_cn):
                    missing_cn_name_fields.append(field_key)
                    issues.append(
                        self._build_issue(
                            issue_id=f"{self.skill_name}-field-cn-{table_index}-{field_index}",
                            object_type="field",
                            object_name=field_key,
                            issue_type="missing_field_cn_name",
                            evidence=["field_name_cn is blank"],
                            suggestion="Add a Chinese display label for the field.",
                            confidence=0.93,
                        )
                    )

                if self.is_blank_text(field.field_description):
                    issues.append(
                        self._build_issue(
                            issue_id=f"{self.skill_name}-field-desc-{table_index}-{field_index}",
                            object_type="field",
                            object_name=field_key,
                            issue_type="missing_field_description",
                            evidence=["field_description is blank"],
                            suggestion="Add a field-level business description.",
                            confidence=0.94,
                        )
                    )
                else:
                    for quality_index, (issue_type, evidence_text) in enumerate(
                        self.collect_description_quality_issues(
                            field.field_name, field.field_description
                        ),
                        start=1,
                    ):
                        issues.append(
                            self._build_issue(
                                issue_id=(
                                    f"{self.skill_name}-field-quality-"
                                    f"{table_index}-{field_index}-{quality_index}"
                                ),
                                object_type="field",
                                object_name=field_key,
                                issue_type=issue_type,
                                evidence=[evidence_text],
                                suggestion="Improve the field description to explain business meaning and valid usage.",
                                confidence=0.76,
                            )
                        )

        total_tables = len(payload.tables)
        table_description_coverage = (
            round(tables_with_description / total_tables, 2) if total_tables else 0.0
        )
        field_cn_name_coverage = (
            round(fields_with_cn_name / total_fields, 2) if total_fields else 0.0
        )
        field_description_coverage = (
            round(fields_with_description / total_fields, 2) if total_fields else 0.0
        )

        # TODO: extend completeness checks with domain, owner, and lifecycle metadata policies.
        return MetadataCompletenessOutput(
            total_tables=total_tables,
            total_fields=total_fields,
            table_description_coverage=table_description_coverage,
            field_cn_name_coverage=field_cn_name_coverage,
            field_description_coverage=field_description_coverage,
            missing_description_tables=missing_description_tables,
            missing_cn_name_fields=missing_cn_name_fields,
            issues=issues,
            summary=(
                f"Checked {total_tables} tables and {total_fields} fields. "
                f"Table description coverage={table_description_coverage:.0%}, "
                f"field CN name coverage={field_cn_name_coverage:.0%}, "
                f"field description coverage={field_description_coverage:.0%}. "
                f"Generated {len(issues)} completeness issues."
            ),
        )

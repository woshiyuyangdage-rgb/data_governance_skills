"""Models for local Text-to-SQL metadata readiness assessment."""

from pydantic import BaseModel, Field

from app.core.models.field_meta import FieldMeta


class TextToSqlMetricDefinition(BaseModel):
    """Business metric metadata needed for reliable Text-to-SQL generation."""

    metric_name: str
    description: str | None = None
    numerator: str | None = None
    denominator: str | None = None
    filters: str | None = None
    time_grain: str | None = None
    status_scope: str | None = None
    unit: str | None = None


class TextToSqlTableRelationship(BaseModel):
    """Declared join path or table relationship for Text-to-SQL."""

    source_table: str
    source_field: str | None = None
    target_table: str
    target_field: str | None = None
    relationship_type: str | None = None
    join_type: str | None = None
    description: str | None = None


class TextToSqlQueryExample(BaseModel):
    """Example question and SQL pair used as Text-to-SQL guidance."""

    question: str
    sql: str | None = None
    business_explanation: str | None = None
    failure_mode: str | None = None


class TextToSqlTableMetadata(BaseModel):
    """Table-level metadata used by Text-to-SQL readiness checks."""

    table_name: str
    table_name_cn: str | None = None
    table_description: str | None = None
    schema_name: str | None = None
    system_name: str | None = None
    business_domain: str | None = None
    data_layer: str | None = None
    lifecycle_status: str | None = None
    sensitivity_label: str | None = None
    permission_label: str | None = None
    masking_policy: str | None = None
    lineage: str | None = None
    primary_key_fields: list[str] = Field(default_factory=list)
    foreign_key_fields: list[str] = Field(default_factory=list)
    fields: list[FieldMeta] = Field(default_factory=list)
    relationships: list[TextToSqlTableRelationship] = Field(default_factory=list)
    metric_definitions: list[TextToSqlMetricDefinition] = Field(default_factory=list)
    enum_definitions: dict[str, dict[str, str]] = Field(default_factory=dict)
    sample_sql: list[TextToSqlQueryExample] = Field(default_factory=list)
    query_log_examples: list[str] = Field(default_factory=list)
    similar_table_names: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class TextToSqlReadinessIssue(BaseModel):
    """Structured issue found during Text-to-SQL metadata readiness assessment."""

    table_name: str
    issue_type: str
    severity: str
    dimension: str
    object_type: str = "table"
    object_name: str | None = None
    evidence: list[str] = Field(default_factory=list)
    risk: str | None = None
    suggestion: str | None = None
    requires_manual_review: bool = False


class TextToSqlReadinessScore(BaseModel):
    """Table-level readiness score for Text-to-SQL consumption."""

    table_name: str
    readiness_score: float = 0.0
    readiness_level: str = "not_recommended"
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    major_gaps: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    requires_manual_review: bool = False


class TextToSqlReadinessAssessmentResult(BaseModel):
    """Text-to-SQL readiness assessment output."""

    table_count: int = 0
    issue_count: int = 0
    scores: list[TextToSqlReadinessScore] = Field(default_factory=list)
    issues: list[TextToSqlReadinessIssue] = Field(default_factory=list)
    summary: dict[str, object] = Field(default_factory=dict)

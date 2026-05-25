"""Table metadata model placeholders."""

from pydantic import BaseModel, Field

from app.core.models.field_meta import FieldMeta


class TableMeta(BaseModel):
    """Basic table metadata used across governance workflows."""

    table_name: str
    table_name_cn: str | None = None
    table_description: str | None = None
    schema_name: str | None = None
    system_name: str | None = None
    business_domain: str | None = None
    owner_role: str | None = None
    lifecycle_status: str | None = None
    data_layer: str | None = None
    catalog_path: str | None = None
    upstream_systems: list[str] = Field(default_factory=list)
    downstream_applications: list[str] = Field(default_factory=list)
    frequent_query_sql: str | None = None
    usage_scenarios: str | None = None
    standard_code: str | None = None
    standard_name: str | None = None
    sensitivity_label: str | None = None
    primary_key_fields: list[str] = Field(default_factory=list)
    foreign_key_fields: list[str] = Field(default_factory=list)
    fields: list[FieldMeta] = Field(default_factory=list)

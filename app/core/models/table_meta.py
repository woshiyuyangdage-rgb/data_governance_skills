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
    fields: list[FieldMeta] = Field(default_factory=list)


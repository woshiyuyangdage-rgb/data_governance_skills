"""Field metadata model placeholders."""

from pydantic import BaseModel


class FieldMeta(BaseModel):
    """Basic field metadata used by parsers and governance skills."""

    field_name: str
    field_name_cn: str | None = None
    field_description: str | None = None
    data_type: str | None = None
    nullable: bool | None = None


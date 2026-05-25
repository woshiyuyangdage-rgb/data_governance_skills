"""Field metadata model placeholders."""

from pydantic import BaseModel


class FieldMeta(BaseModel):
    """Basic field metadata used by parsers and governance skills."""

    field_name: str
    field_name_cn: str | None = None
    field_description: str | None = None
    data_type: str | None = None
    data_length: str | None = None
    sample_values: str | None = None
    nullable: bool | None = None
    standard_code: str | None = None
    standard_name: str | None = None
    business_domain: str | None = None
    owner_role: str | None = None
    is_primary_key: bool | None = None
    is_foreign_key: bool | None = None
    is_sensitive: bool | None = None
    lifecycle_status: str | None = None
    catalog_path: str | None = None

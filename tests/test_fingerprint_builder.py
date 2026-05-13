"""Tests for metadata fingerprint generation."""

from app.core.governance.fingerprint_builder import FingerprintBuilder
from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta


def test_fingerprint_builder_generates_stable_fingerprints() -> None:
    table = TableMeta(
        table_name="customer",
        system_name="crm",
        schema_name="ods",
        fields=[FieldMeta(field_name="customer_id", data_type="string")],
    )
    builder = FingerprintBuilder()

    first = builder.build_table_fingerprint(table, group_name="crm")
    second = builder.build_table_fingerprint(table, group_name="crm")

    assert first.fingerprint == second.fingerprint
    assert first.object_name == "crm.ods.customer"


def test_fingerprint_changes_when_metadata_changes() -> None:
    builder = FingerprintBuilder()
    original = TableMeta(
        table_name="customer",
        fields=[FieldMeta(field_name="customer_id", data_type="string")],
    )
    changed = TableMeta(
        table_name="customer",
        fields=[FieldMeta(field_name="customer_id", data_type="int")],
    )

    assert (
        builder.build_table_fingerprint(original).fingerprint
        != builder.build_table_fingerprint(changed).fingerprint
    )


"""Smoke tests for naming rule checks."""

from app.core.models.field_meta import FieldMeta
from app.core.models.table_meta import TableMeta
from app.core.skills.metadata_diagnosis_skill import (
    NamingStandardCheckInput,
    NamingStandardCheckSkill,
)


def test_naming_skill_generates_issues_and_suggestions() -> None:
    skill = NamingStandardCheckSkill()
    table = TableMeta(
        table_name="TMP Sales__Order",
        table_name_cn="sales order",
        table_description="Order header table.",
        fields=[
            FieldMeta(
                field_name="Cust ID",
                field_name_cn="customer id",
                field_description="Customer identifier.",
                data_type="string",
                nullable=False,
            )
        ],
    )

    result = skill.run(NamingStandardCheckInput(tables=[table]))

    assert result.issues
    assert result.table_name_suggestions["TMP Sales__Order"] == "sales_order"
    assert "TMP Sales__Order.Cust ID" in result.field_name_suggestions

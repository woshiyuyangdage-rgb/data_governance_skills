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


def test_naming_skill_flags_likely_spelling_errors() -> None:
    skill = NamingStandardCheckSkill()
    table = TableMeta(
        table_name="sales_order",
        table_name_cn="sales order",
        table_description="Order header table.",
        fields=[
            FieldMeta(
                field_name="transaciton_id",
                field_name_cn="transaction id",
                field_description="Transaction identifier.",
                data_type="string",
                nullable=False,
            )
        ],
    )

    result = skill.run(NamingStandardCheckInput(tables=[table]))

    spelling_issues = [
        issue
        for issue in result.issues
        if issue.issue_type == "naming_suspected_spelling_error"
    ]
    assert spelling_issues
    assert result.field_name_suggestions["sales_order.transaciton_id"] == "transaction_identifier"
    assert any("transaciton" in evidence for evidence in spelling_issues[0].evidence)
    assert any("transaction" in evidence for evidence in spelling_issues[0].evidence)

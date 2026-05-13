"""Tests for enterprise delivery layout adaptation."""

import pandas as pd

from app.core.delivery.enterprise_delivery_adapter import EnterpriseDeliveryAdapter


def test_enterprise_delivery_adapter_applies_mapping_layout() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "source_table_name": "customer",
                "source_field_name": "customer_id",
                "confirmation_status": "pending",
            }
        ]
    )

    adapted = EnterpriseDeliveryAdapter().adapt_mapping_confirmation_workbook(dataframe)

    assert adapted.sheet_name == "mapping_review"
    assert "Source Table" in adapted.dataframe.columns
    assert "review_owner" in adapted.dataframe.columns
    assert adapted.result.extra_columns_added == ["review_owner", "business_comment"]


def test_enterprise_delivery_adapter_applies_stg_quality_and_backlog_layouts() -> None:
    adapter = EnterpriseDeliveryAdapter()

    stg = adapter.adapt_stg_confirmation_workbook(
        pd.DataFrame(
            [
                {
                    "source_table_name": "customer",
                    "source_field_name": "customer_id",
                    "confirmation_status": "pending",
                }
            ]
        )
    )
    quality = adapter.adapt_quality_rule_confirmation_workbook(
        pd.DataFrame(
            [
                {
                    "source_table_name": "customer",
                    "rule_type": "not_null",
                    "confirmation_status": "pending",
                }
            ]
        )
    )
    backlog = adapter.adapt_backlog_delivery_workbook(
        pd.DataFrame(
            [
                {
                    "backlog_id": "backlog_1",
                    "object_name": "customer.customer_id",
                }
            ]
        )
    )

    assert stg.sheet_name == "stg_design_review"
    assert "architect_comment" in stg.dataframe.columns
    assert quality.sheet_name == "quality_rule_review"
    assert "rule_owner" in quality.dataframe.columns
    assert backlog.sheet_name == "governance_backlog"
    assert "due_note" in backlog.dataframe.columns


def test_enterprise_delivery_adapter_filters_bundle_variant() -> None:
    result = EnterpriseDeliveryAdapter().adapt_governance_delivery_package(
        {
            "mapping_confirmation_workbook": "mapping.xlsx",
            "quality_rule_confirmation_workbook": "quality.xlsx",
            "package_manifest": "manifest.json",
            "stg_confirmation_workbook": "stg.xlsx",
        },
        "business_confirmation_bundle",
    )

    assert result.status == "success"
    assert set(result.generated_files) == {
        "mapping_confirmation_workbook",
        "quality_rule_confirmation_workbook",
        "governance_delivery_manifest",
    }

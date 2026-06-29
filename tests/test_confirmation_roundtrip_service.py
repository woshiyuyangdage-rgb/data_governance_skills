"""Tests for confirmation round-trip merge service."""

from pathlib import Path

import pandas as pd

from app.core.delivery.confirmation_roundtrip_service import (
    ConfirmationRoundTripService,
)
from app.core.delivery.confirmation_workbook_importer import (
    ConfirmationWorkbookImporter,
    WorkbookImportPayload,
)
from app.core.governance import backlog_store
from app.core.models.governance_backlog_item import GovernanceBacklogItem
from app.core.models.workbook_import_summary import WorkbookImportSummary
from app.core.models.workbook_validation_result import WorkbookValidationResult
from app.core.review import override_store, quality_override_store


def _payload(workbook_type: str, rows: list[dict[str, object]]) -> WorkbookImportPayload:
    return WorkbookImportPayload(
        workbook_type=workbook_type,
        validation_result=WorkbookValidationResult(
            workbook_type=workbook_type,
            is_valid=True,
        ),
        import_summary=WorkbookImportSummary(
            workbook_type=workbook_type,
            total_rows=len(rows),
            imported_count=len(rows),
            skipped_count=0,
            invalid_count=0,
            accepted_count=1 if rows else 0,
            rejected_count=0,
            edited_count=0,
            manual_review_count=0,
        ),
        normalized_rows=rows,
    )


def test_roundtrip_generates_mapping_stg_quality_records(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(override_store, "MAPPING_OVERRIDES_PATH", tmp_path / "mapping.csv")
    monkeypatch.setattr(override_store, "STG_OVERRIDES_PATH", tmp_path / "stg.csv")
    monkeypatch.setattr(override_store, "REVIEW_SESSIONS_DIR", tmp_path / "sessions")
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_OVERRIDES_PATH",
        tmp_path / "quality.csv",
    )
    monkeypatch.setattr(
        quality_override_store,
        "QUALITY_RULE_SESSIONS_DIR",
        tmp_path / "quality_sessions",
    )
    service = ConfirmationRoundTripService()

    mapping_result = service.apply_roundtrip_updates(
        _payload(
            "mapping_confirmation",
            [
                {
                    "source_table_name": "customer",
                    "source_field_name": "customer_id",
                    "recommended_standard_code": "customer_id",
                    "confirmation_status": "accept",
                    "object_key": "customer.customer_id",
                }
            ],
        )
    )
    stg_result = service.apply_roundtrip_updates(
        _payload(
            "stg_confirmation",
            [
                {
                    "source_table_name": "customer",
                    "source_field_name": "customer_id",
                    "recommended_stg_field_name": "customer_id",
                    "confirmation_status": "accept",
                    "object_key": "customer.customer_id",
                }
            ],
        )
    )
    quality_result = service.apply_roundtrip_updates(
        _payload(
            "quality_rule_confirmation",
            [
                {
                    "source_table_name": "customer",
                    "source_field_name": "customer_id",
                    "rule_type": "not_null",
                    "rule_expression": "not_null",
                    "severity": "high",
                    "confirmation_status": "accept",
                    "object_key": "customer.customer_id.not_null",
                }
            ],
        )
    )

    assert mapping_result.generated_review_records_count == 1
    assert stg_result.generated_override_updates_count == 1
    assert quality_result.changed_object_keys == ["customer.customer_id.not_null"]


def test_roundtrip_updates_backlog_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(backlog_store, "BACKLOG_DIR", tmp_path)
    monkeypatch.setattr(backlog_store, "BACKLOG_ITEMS_PATH", tmp_path / "items.json")
    monkeypatch.setattr(backlog_store, "BACKLOG_SNAPSHOTS_DIR", tmp_path / "snapshots")
    backlog_store.save_backlog_items(
        [
            GovernanceBacklogItem(
                backlog_id="backlog_1",
                object_type="field",
                object_name="customer.customer_id",
                gap_type="quality_rule_gap",
                action="Confirm rule",
                owner_role="data_steward",
                priority="high",
                status="proposed",
            )
        ]
    )

    result = ConfirmationRoundTripService().apply_roundtrip_updates(
        _payload(
            "backlog_confirmation",
            [
                {
                    "backlog_id": "backlog_1",
                    "confirmation_status": "accepted",
                    "object_key": "backlog_1",
                }
            ],
        )
    )

    assert result.generated_backlog_updates_count == 1
    assert backlog_store.get_backlog_item("backlog_1").status == "accepted"


def test_template_aware_import_rows_can_enter_roundtrip_merge(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(override_store, "MAPPING_OVERRIDES_PATH", tmp_path / "mapping.csv")
    monkeypatch.setattr(override_store, "REVIEW_SESSIONS_DIR", tmp_path / "sessions")
    workbook_path = tmp_path / "business_mapping.xlsx"
    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame(
            [
                {
                    "表名": "customer",
                    "字段名": "customer_id",
                    "标准编码": "customer_id",
                    "确认结果": "accepted",
                }
            ]
        ).to_excel(writer, sheet_name="mapping_review", index=False)

    payload = ConfirmationWorkbookImporter().import_confirmation_with_template(
        str(workbook_path),
        workbook_type="mapping_confirmation",
    )
    result = ConfirmationRoundTripService().apply_roundtrip_updates(payload)

    assert payload.confirmation_template_mapping_result is not None
    assert result.generated_review_records_count == 1
    assert result.changed_object_keys == ["customer.customer_id"]


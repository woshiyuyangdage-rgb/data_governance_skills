"""Merge imported confirmation workbooks back into local governance stores."""

from datetime import datetime
from typing import Any

from app.core.delivery.confirmation_workbook_importer import WorkbookImportPayload
from app.core.governance import backlog_store
from app.core.governance.backlog_tracking_service import GovernanceBacklogTrackingService
from app.core.models.confirmation_roundtrip_result import ConfirmationRoundTripResult
from app.core.models.mapping_review_record import MappingReviewRecord
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.stg_review_record import StgReviewRecord
from app.core.review.override_store import (
    save_mapping_review_records,
    save_stg_review_records,
)
from app.core.review.quality_override_store import save_quality_rule_review_records


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class ConfirmationRoundTripService:
    """Convert imported workbook rows into review records and status updates."""

    @staticmethod
    def _text(value: object) -> str:
        return str(value or "").strip()

    def build_mapping_review_records_from_workbook_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[MappingReviewRecord]:
        """Build mapping review records from normalized workbook rows."""
        records: list[MappingReviewRecord] = []
        for row in rows:
            action = self._text(row.get("confirmation_status"))
            standard_code = self._text(row.get("recommended_standard_code")) or None
            records.append(
                MappingReviewRecord(
                    table_name=self._text(row.get("source_table_name")),
                    field_name=self._text(row.get("source_field_name")),
                    original_recommended_standard_code=standard_code,
                    final_standard_code=standard_code if action in {"accept", "edit"} else None,
                    review_action=action,
                    reviewer_note=self._text(row.get("reviewer_note")) or None,
                    reviewed_at=_utc_now(),
                    source="confirmation_workbook_import",
                )
            )
        return records

    def build_stg_review_records_from_workbook_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[StgReviewRecord]:
        """Build STG review records from normalized workbook rows."""
        records: list[StgReviewRecord] = []
        for row in rows:
            action = self._text(row.get("confirmation_status"))
            stg_field = self._text(row.get("recommended_stg_field_name")) or None
            data_type = self._text(row.get("recommended_data_type")) or None
            records.append(
                StgReviewRecord(
                    source_table_name=self._text(row.get("source_table_name")),
                    source_field_name=self._text(row.get("source_field_name")),
                    original_recommended_stg_field_name=stg_field,
                    final_stg_field_name=stg_field if action in {"accept", "edit"} else None,
                    original_recommended_data_type=data_type,
                    final_data_type=data_type if action in {"accept", "edit"} else None,
                    review_action=action,
                    reviewer_note=self._text(row.get("reviewer_note")) or None,
                    reviewed_at=_utc_now(),
                    source="confirmation_workbook_import",
                )
            )
        return records

    def build_quality_review_records_from_workbook_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[QualityRuleReviewRecord]:
        """Build quality rule review records from normalized workbook rows."""
        records: list[QualityRuleReviewRecord] = []
        for row in rows:
            field_group = row.get("field_group") or []
            if isinstance(field_group, str):
                field_group = [item.strip() for item in field_group.split(",") if item.strip()]
            action = self._text(row.get("confirmation_status"))
            expression = self._text(row.get("rule_expression")) or None
            severity = self._text(row.get("severity")) or None
            records.append(
                QualityRuleReviewRecord(
                    source_table_name=self._text(row.get("source_table_name")),
                    source_field_name=self._text(row.get("source_field_name")),
                    rule_scope=self._text(row.get("rule_scope")) or "field",
                    field_group=field_group if isinstance(field_group, list) else [],
                    rule_type=self._text(row.get("rule_type")),
                    original_rule_expression=expression,
                    final_rule_expression=expression if action in {"accept", "edit"} else None,
                    original_severity=severity,
                    final_severity=severity if action in {"accept", "edit"} else None,
                    review_action=action,
                    reviewer_note=self._text(row.get("reviewer_note")) or None,
                    reviewed_at=_utc_now(),
                    source="confirmation_workbook_import",
                )
            )
        return records

    def build_backlog_status_updates_from_workbook_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> list[dict[str, str | None]]:
        """Build backlog status update payloads from normalized workbook rows."""
        updates: list[dict[str, str | None]] = []
        for row in rows:
            new_status = self._text(row.get("new_status")) or self._text(
                row.get("confirmation_status")
            )
            updates.append(
                {
                    "backlog_id": self._text(row.get("backlog_id")),
                    "new_status": new_status,
                    "note": self._text(row.get("reviewer_note")) or None,
                }
            )
        return updates

    def apply_roundtrip_updates(
        self,
        import_payload: WorkbookImportPayload,
        persist: bool = True,
    ) -> ConfirmationRoundTripResult:
        """Persist imported workbook decisions into local stores."""
        workbook_type = import_payload.workbook_type
        rows = import_payload.normalized_rows
        changed_keys = [str(row.get("object_key")) for row in rows if row.get("object_key")]
        review_count = 0
        override_count = 0
        backlog_update_count = 0

        if persist and rows:
            if workbook_type == "mapping_confirmation":
                records = self.build_mapping_review_records_from_workbook_rows(rows)
                save_mapping_review_records(records)
                review_count = override_count = len(records)
            elif workbook_type == "stg_confirmation":
                records = self.build_stg_review_records_from_workbook_rows(rows)
                save_stg_review_records(records)
                review_count = override_count = len(records)
            elif workbook_type == "quality_rule_confirmation":
                records = self.build_quality_review_records_from_workbook_rows(rows)
                save_quality_rule_review_records(records)
                review_count = override_count = len(records)
            elif workbook_type == "backlog_confirmation":
                service = GovernanceBacklogTrackingService()
                for update in self.build_backlog_status_updates_from_workbook_rows(rows):
                    current_item = backlog_store.get_backlog_item(str(update["backlog_id"]))
                    if current_item is None:
                        continue
                    service.update_backlog_status(
                        str(update["backlog_id"]),
                        str(update["new_status"]),
                        update.get("note"),
                    )
                    backlog_update_count += 1

        status = "success" if import_payload.import_summary.invalid_count == 0 else "partial_success"
        return ConfirmationRoundTripResult(
            workbook_type=workbook_type,
            import_summary=import_payload.import_summary,
            generated_review_records_count=review_count,
            generated_override_updates_count=override_count,
            generated_backlog_updates_count=backlog_update_count,
            changed_object_keys=changed_keys,
            status=status,
            message=(
                f"Round-trip merge completed for {workbook_type}: "
                f"{len(changed_keys)} changed objects."
            ),
        )


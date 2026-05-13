"""Excel confirmation workbook exporter for governance delivery artifacts."""

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.models.confirmation_workbook_result import ConfirmationWorkbookResult
from app.core.rules.config_loader import (
    get_confirmation_workbook_policies_config,
    get_governance_delivery_templates_config,
)
from app.core.utils.file_utils import ensure_directory


class ConfirmationWorkbookExporter:
    """Export reviewer-facing confirmation workbooks."""

    def __init__(self) -> None:
        self.templates = get_governance_delivery_templates_config().get("templates", {})
        self.policies = get_confirmation_workbook_policies_config()

    def _template_columns(self, template_name: str) -> list[str]:
        template = self.templates.get(template_name, {})
        return list(template.get("include_columns", []))

    def _workbook_policy(self) -> dict[str, Any]:
        return dict(self.policies.get("workbook_policy", {}))

    def _default_confirmation_status(self) -> str:
        return str(self._workbook_policy().get("default_confirmation_status", "pending"))

    @staticmethod
    def _model_to_dict(item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if hasattr(item, "dict"):
            return item.dict()
        if isinstance(item, dict):
            return dict(item)
        return {}

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return str(value)
        return value

    def _select_columns(self, rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
        normalized_rows = []
        for row in rows:
            normalized_rows.append(
                {column: self._stringify(row.get(column)) for column in columns}
            )
        return pd.DataFrame(normalized_rows, columns=columns)

    def _write_workbook(
        self,
        output_path: str,
        workbook_type: str,
        data_df: pd.DataFrame,
        data_sheet_name: str,
    ) -> ConfirmationWorkbookResult:
        path = Path(output_path)
        ensure_directory(path.parent)
        policy = self._workbook_policy()
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            if bool(policy.get("include_instruction_sheet", True)):
                pd.DataFrame(
                    [
                        {
                            "instruction": (
                                "Review each row, update confirmation_status, and add reviewer_note when needed."
                            )
                        },
                        {
                            "instruction": (
                                "Suggested statuses: pending, accepted, rejected, edited, manual_review."
                            )
                        },
                    ]
                ).to_excel(writer, sheet_name="instructions", index=False)
            if bool(policy.get("include_summary_sheet", True)):
                pd.DataFrame(
                    [
                        {
                            "workbook_type": workbook_type,
                            "row_count": len(data_df),
                            "default_confirmation_status": self._default_confirmation_status(),
                        }
                    ]
                ).to_excel(writer, sheet_name="summary", index=False)
            data_df.to_excel(writer, sheet_name=data_sheet_name, index=False)
        return ConfirmationWorkbookResult(
            workbook_type=workbook_type,
            output_path=str(path),
            row_count=len(data_df),
            status="success",
            message=f"{workbook_type} workbook exported.",
        )

    def export_mapping_confirmation_workbook(
        self,
        mapping_results: list[Any],
        output_path: str,
    ) -> ConfirmationWorkbookResult:
        """Export standard mapping recommendations for manual confirmation."""
        rows = []
        for item in mapping_results:
            payload = self._model_to_dict(item)
            rows.append(
                {
                    "source_table_name": payload.get("source_table_name")
                    or payload.get("table_name"),
                    "source_field_name": payload.get("source_field_name")
                    or payload.get("field_name"),
                    "source_field_name_cn": payload.get("source_field_name_cn")
                    or payload.get("field_name_cn"),
                    "recommended_standard_code": payload.get("recommended_standard_code"),
                    "recommended_standard_name": payload.get("recommended_standard_name"),
                    "recommended_standard_name_cn": payload.get(
                        "recommended_standard_name_cn"
                    ),
                    "match_score": payload.get("match_score"),
                    "match_reason": payload.get("match_reason"),
                    "confirmation_status": payload.get("review_action")
                    or self._default_confirmation_status(),
                    "reviewer_note": payload.get("reviewer_note") or "",
                }
            )
        df = self._select_columns(rows, self._template_columns("mapping_confirmation"))
        return self._write_workbook(
            output_path,
            "mapping_confirmation",
            df,
            "mapping_confirmation",
        )

    def export_stg_confirmation_workbook(
        self,
        stg_suggestions: list[Any],
        output_path: str,
    ) -> ConfirmationWorkbookResult:
        """Export STG field suggestions for manual confirmation."""
        rows = []
        for item in stg_suggestions:
            payload = self._model_to_dict(item)
            rows.append(
                {
                    "source_table_name": payload.get("source_table_name"),
                    "source_field_name": payload.get("source_field_name"),
                    "recommended_stg_field_name": payload.get(
                        "recommended_stg_field_name"
                    ),
                    "recommended_stg_field_name_cn": payload.get(
                        "recommended_stg_field_name_cn"
                    ),
                    "recommended_data_type": payload.get("recommended_data_type"),
                    "mapping_source": payload.get("mapping_source"),
                    "action": payload.get("review_action") or payload.get("action"),
                    "confirmation_status": payload.get("review_action")
                    or self._default_confirmation_status(),
                    "reviewer_note": payload.get("reviewer_note") or "",
                }
            )
        df = self._select_columns(rows, self._template_columns("stg_confirmation"))
        return self._write_workbook(
            output_path,
            "stg_confirmation",
            df,
            "stg_confirmation",
        )

    def export_quality_rule_confirmation_workbook(
        self,
        quality_rules: list[Any],
        output_path: str,
    ) -> ConfirmationWorkbookResult:
        """Export field-level and cross-field quality rules for confirmation."""
        rows = []
        for item in quality_rules:
            payload = self._model_to_dict(item)
            field_group = payload.get("field_group") or []
            source_field_name = payload.get("source_field_name")
            if not source_field_name and field_group:
                source_field_name = ", ".join(str(field) for field in field_group)
            rows.append(
                {
                    "source_table_name": payload.get("source_table_name"),
                    "source_field_name": source_field_name,
                    "rule_scope": payload.get("rule_scope") or "cross_field",
                    "field_group": field_group,
                    "rule_type": payload.get("rule_type"),
                    "rule_expression": payload.get("rule_expression"),
                    "severity": payload.get("severity"),
                    "confidence": payload.get("confidence"),
                    "review_priority": payload.get("review_priority"),
                    "confirmation_status": payload.get("review_action")
                    or self._default_confirmation_status(),
                    "reviewer_note": payload.get("reviewer_note") or "",
                }
            )
        df = self._select_columns(
            rows,
            self._template_columns("quality_rule_confirmation"),
        )
        return self._write_workbook(
            output_path,
            "quality_rule_confirmation",
            df,
            "quality_rule_confirmation",
        )

    def export_backlog_delivery_workbook(
        self,
        backlog_items: list[Any],
        output_path: str,
    ) -> ConfirmationWorkbookResult:
        """Export remediation/backlog items as a local delivery workbook."""
        rows = []
        for item in backlog_items:
            payload = self._model_to_dict(item)
            rows.append(
                {
                    "backlog_id": payload.get("backlog_id"),
                    "object_type": payload.get("object_type"),
                    "object_name": payload.get("object_name"),
                    "gap_type": payload.get("gap_type"),
                    "action": payload.get("action"),
                    "owner_role": payload.get("owner_role"),
                    "priority": payload.get("priority"),
                    "status": payload.get("status"),
                    "completion_criteria": payload.get("completion_criteria"),
                    "dependency_notes": payload.get("dependency_notes"),
                }
            )
        df = self._select_columns(
            rows,
            self._template_columns("remediation_backlog_delivery"),
        )
        return self._write_workbook(
            output_path,
            "remediation_backlog_delivery",
            df,
            "remediation_backlog",
        )


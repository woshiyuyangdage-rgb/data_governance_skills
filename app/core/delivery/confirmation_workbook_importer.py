"""Import and validate confirmation workbooks."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.delivery.confirmation_template_loader import (
    get_confirmation_template_profile,
    load_confirmation_template_mapping_specs,
)
from app.core.delivery.confirmation_template_matcher import ConfirmationTemplateMatcher
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.confirmation_template_mapping_result import (
    ConfirmationTemplateMappingResult,
)
from app.core.models.workbook_import_row_result import WorkbookImportRowResult
from app.core.models.workbook_import_summary import WorkbookImportSummary
from app.core.models.workbook_validation_result import WorkbookValidationResult
from app.core.rules.config_loader import (
    get_workbook_column_aliases_config,
    get_workbook_import_policies_config,
)


REQUIRED_COLUMNS = {
    "mapping_confirmation": [
        "source_table_name",
        "source_field_name",
        "confirmation_status",
    ],
    "stg_confirmation": [
        "source_table_name",
        "source_field_name",
        "confirmation_status",
    ],
    "quality_rule_confirmation": [
        "source_table_name",
        "rule_type",
        "confirmation_status",
    ],
    "backlog_confirmation": [
        "backlog_id",
        "confirmation_status",
    ],
}


@dataclass
class WorkbookImportPayload:
    """Structured payload returned by workbook importer."""

    workbook_type: str
    validation_result: WorkbookValidationResult
    import_summary: WorkbookImportSummary
    row_results: list[WorkbookImportRowResult] = field(default_factory=list)
    normalized_rows: list[dict[str, Any]] = field(default_factory=list)
    confirmation_template_match_result: ConfirmationTemplateMatchResult | None = None
    confirmation_template_mapping_result: ConfirmationTemplateMappingResult | None = None


class ConfirmationWorkbookImporter:
    """Validate and import round-trip confirmation workbooks."""

    def __init__(self) -> None:
        self.policies = get_workbook_import_policies_config()
        self.aliases = get_workbook_column_aliases_config().get("aliases", {})

    def detect_main_sheet(self, file_path: str, workbook_type: str) -> str:
        """Detect the main workbook sheet from configured candidates."""
        path = Path(file_path)
        if path.suffix.lower() == ".csv":
            return ""
        excel = pd.ExcelFile(file_path)
        sheet_lookup = {sheet.lower(): sheet for sheet in excel.sheet_names}
        workbook_config = self.policies.get("workbook_types", {}).get(workbook_type, {})
        candidates = workbook_config.get("main_sheet_candidates", [])
        for candidate in candidates:
            if str(candidate).lower() in sheet_lookup:
                return sheet_lookup[str(candidate).lower()]
        if bool(self.policies.get("import_policy", {}).get("default_sheet_name_fallback", True)):
            return excel.sheet_names[-1]
        raise ValueError(f"No supported sheet was found for workbook type '{workbook_type}'.")

    @staticmethod
    def _normalize_column_name(value: object) -> str:
        return str(value or "").strip().lower()

    def normalize_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """Normalize configured column aliases to canonical column names."""
        alias_lookup: dict[str, str] = {}
        for canonical, aliases in self.aliases.items():
            alias_lookup[self._normalize_column_name(canonical)] = canonical
            for alias in aliases or []:
                alias_lookup[self._normalize_column_name(alias)] = canonical
        renamed = {}
        for column in dataframe.columns:
            normalized = self._normalize_column_name(column)
            renamed[column] = alias_lookup.get(normalized, normalized)
        return dataframe.rename(columns=renamed)

    def normalize_confirmation_status(self, status: object) -> str | None:
        """Normalize reviewer status to local review action values."""
        text = str(status or "").strip().lower()
        if not text:
            return None
        mapping = self.policies.get("confirmation_status_mapping", {})
        return mapping.get(text)

    @staticmethod
    def _read_dataframe(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
        path = Path(file_path)
        extension = path.suffix.lower()
        if extension == ".csv":
            return pd.read_csv(path)
        if extension in {".xlsx", ".xls"}:
            return pd.read_excel(path, sheet_name=sheet_name or 0)
        raise ValueError(f"Unsupported confirmation workbook file type '{extension or '<none>'}'.")

    @staticmethod
    def _clean_value(value: object) -> object | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_template_header(value: object) -> str:
        return str(value or "").strip().replace(" ", "").replace("_", "").lower()

    def diagnose_confirmation_template(
        self,
        file_path: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> ConfirmationTemplateMatchResult:
        """Diagnose confirmation workbook template from headers."""
        return ConfirmationTemplateMatcher().match(
            file_path,
            workbook_type=workbook_type,
            sheet_name=sheet_name,
        )

    def build_template_mapping_result(
        self,
        dataframe: pd.DataFrame,
        template_name: str,
    ) -> ConfirmationTemplateMappingResult:
        """Map source columns to target confirmation fields using a template spec."""
        profile = get_confirmation_template_profile(template_name)
        spec = load_confirmation_template_mapping_specs().get(profile.mapping_spec_name)
        if spec is None:
            raise ValueError(f"Mapping spec '{profile.mapping_spec_name}' was not found.")
        source_columns = [str(column).strip() for column in dataframe.columns]
        normalized_source = {
            self._normalize_template_header(column): column for column in source_columns
        }
        target_fields = list(profile.required_target_fields) + list(profile.optional_target_fields)
        mapped_fields: dict[str, str] = {}
        for target_field in target_fields:
            aliases = [target_field] + list(spec.get(target_field, []))
            for alias in aliases:
                normalized_alias = self._normalize_template_header(alias)
                if normalized_alias in normalized_source:
                    mapped_fields[target_field] = normalized_source[normalized_alias]
                    break
        mapped_source = set(mapped_fields.values())
        missing_required = [
            field for field in profile.required_target_fields if field not in mapped_fields
        ]
        unmapped = [column for column in source_columns if column not in mapped_source]
        status = "success" if not missing_required else "failed"
        return ConfirmationTemplateMappingResult(
            template_name=profile.template_name,
            workbook_type=profile.workbook_type,
            source_columns=source_columns,
            mapped_fields=mapped_fields,
            unmapped_source_columns=unmapped,
            missing_required_fields=missing_required,
            status=status,
            message=(
                "Confirmation workbook columns mapped to target fields."
                if status == "success"
                else "Required target fields are missing: " + ", ".join(missing_required)
            ),
        )

    def dataframe_from_template_mapping(
        self,
        dataframe: pd.DataFrame,
        mapping_result: ConfirmationTemplateMappingResult,
    ) -> pd.DataFrame:
        """Build a canonical confirmation dataframe from template mapping."""
        rows: list[dict[str, Any]] = []
        target_fields = set(mapping_result.mapped_fields.keys()).union(
            set(REQUIRED_COLUMNS.get(mapping_result.workbook_type, []))
        )
        for raw_row in dataframe.to_dict("records"):
            row: dict[str, Any] = {}
            for target_field in target_fields:
                source_column = mapping_result.mapped_fields.get(target_field)
                row[target_field] = self._clean_value(raw_row.get(source_column)) if source_column else None
            rows.append(row)
        return pd.DataFrame(rows)

    def validate_workbook(
        self,
        file_path: str,
        workbook_type: str,
    ) -> WorkbookValidationResult:
        """Validate workbook sheet and required columns."""
        messages: list[str] = []
        warnings: list[str] = []
        try:
            path = Path(file_path)
            sheet_name = None if path.suffix.lower() == ".csv" else self.detect_main_sheet(file_path, workbook_type)
            dataframe = self._read_dataframe(file_path, sheet_name=sheet_name)
            dataframe = self.normalize_columns(dataframe)
        except Exception as exc:
            return WorkbookValidationResult(
                workbook_type=workbook_type,
                is_valid=False,
                messages=[f"Failed to read workbook: {exc}"],
            )
        required = REQUIRED_COLUMNS.get(workbook_type, [])
        present = [column for column in required if column in dataframe.columns]
        missing = [column for column in required if column not in dataframe.columns]
        if missing:
            messages.append(f"Missing required columns: {', '.join(missing)}")
        if dataframe.empty:
            warnings.append("Workbook main sheet is empty.")
        return WorkbookValidationResult(
            workbook_type=workbook_type,
            is_valid=not missing,
            detected_sheet_name=sheet_name,
            required_columns_present=present,
            missing_required_columns=missing,
            warnings=warnings,
            messages=messages,
        )

    @staticmethod
    def build_row_object_key(workbook_type: str, row: dict[str, Any]) -> str | None:
        """Build a stable object key from one normalized workbook row."""
        if workbook_type == "backlog_confirmation":
            return str(row.get("backlog_id") or "").strip() or None
        table = str(row.get("source_table_name") or "").strip()
        field_name = str(row.get("source_field_name") or "").strip()
        if workbook_type == "quality_rule_confirmation":
            rule_type = str(row.get("rule_type") or "").strip()
            return ".".join(part for part in [table, field_name, rule_type] if part) or None
        return ".".join(part for part in [table, field_name] if part) or None

    def summarize_import_results(
        self,
        workbook_type: str,
        row_results: list[WorkbookImportRowResult],
        normalized_rows: list[dict[str, Any]],
    ) -> WorkbookImportSummary:
        """Build import count summary."""
        action_counts = {"accept": 0, "reject": 0, "edit": 0, "mark_for_manual_review": 0}
        for row in normalized_rows:
            action = str(row.get("confirmation_status") or "")
            if action in action_counts:
                action_counts[action] += 1
        imported_count = sum(1 for row in row_results if row.status == "imported")
        skipped_count = sum(1 for row in row_results if row.status == "skipped")
        invalid_count = sum(1 for row in row_results if row.status == "invalid")
        return WorkbookImportSummary(
            workbook_type=workbook_type,
            total_rows=len(row_results),
            imported_count=imported_count,
            skipped_count=skipped_count,
            invalid_count=invalid_count,
            accepted_count=action_counts["accept"],
            rejected_count=action_counts["reject"],
            edited_count=action_counts["edit"],
            manual_review_count=action_counts["mark_for_manual_review"],
            summary=(
                f"{imported_count} imported, {skipped_count} skipped, "
                f"{invalid_count} invalid."
            ),
        )

    def _import_normalized_dataframe(
        self,
        dataframe: pd.DataFrame,
        workbook_type: str,
        validation: WorkbookValidationResult,
        template_match: ConfirmationTemplateMatchResult | None = None,
        template_mapping: ConfirmationTemplateMappingResult | None = None,
    ) -> WorkbookImportPayload:
        """Import one already-normalized confirmation dataframe."""
        if not validation.is_valid:
            summary = WorkbookImportSummary(
                workbook_type=workbook_type,
                total_rows=0,
                imported_count=0,
                skipped_count=0,
                invalid_count=0,
                accepted_count=0,
                rejected_count=0,
                edited_count=0,
                manual_review_count=0,
                summary="Workbook validation failed.",
            )
            return WorkbookImportPayload(
                workbook_type,
                validation,
                summary,
                [],
                [],
                template_match,
                template_mapping,
            )

        dataframe = dataframe.where(pd.notna(dataframe), None)
        policy = self.policies.get("import_policy", {})
        row_results: list[WorkbookImportRowResult] = []
        normalized_rows: list[dict[str, Any]] = []
        required = REQUIRED_COLUMNS.get(workbook_type, [])

        for index, raw_row in enumerate(dataframe.to_dict("records"), start=2):
            row = dict(raw_row)
            if bool(policy.get("skip_empty_rows", True)) and not any(
                str(value or "").strip() for value in row.values()
            ):
                row_results.append(
                    WorkbookImportRowResult(
                        workbook_type=workbook_type,
                        row_index=index,
                        status="skipped",
                        message="Empty row skipped.",
                    )
                )
                continue
            missing_values = [
                column for column in required if not str(row.get(column) or "").strip()
            ]
            object_key = self.build_row_object_key(workbook_type, row)
            if missing_values:
                row_results.append(
                    WorkbookImportRowResult(
                        workbook_type=workbook_type,
                        row_index=index,
                        object_key=object_key,
                        status="invalid",
                        message=f"Missing required values: {', '.join(missing_values)}",
                    )
                )
                continue
            normalized_status = self.normalize_confirmation_status(row.get("confirmation_status"))
            if workbook_type == "backlog_confirmation" and normalized_status is None:
                normalized_status = str(row.get("confirmation_status") or "").strip()
            if normalized_status is None:
                row_results.append(
                    WorkbookImportRowResult(
                        workbook_type=workbook_type,
                        row_index=index,
                        object_key=object_key,
                        status="invalid",
                        message="Unknown confirmation_status.",
                    )
                )
                continue
            if normalized_status == "pending":
                row_results.append(
                    WorkbookImportRowResult(
                        workbook_type=workbook_type,
                        row_index=index,
                        object_key=object_key,
                        status="skipped",
                        message="Pending row skipped.",
                    )
                )
                continue
            row["confirmation_status"] = normalized_status
            row["reviewer_note"] = row.get("reviewer_note") or ""
            row["object_key"] = object_key
            normalized_rows.append(row)
            row_results.append(
                WorkbookImportRowResult(
                    workbook_type=workbook_type,
                    row_index=index,
                    object_key=object_key,
                    status="imported",
                    message="Row imported.",
                )
            )

        summary = self.summarize_import_results(workbook_type, row_results, normalized_rows)
        return WorkbookImportPayload(
            workbook_type=workbook_type,
            validation_result=validation,
            import_summary=summary,
            row_results=row_results,
            normalized_rows=normalized_rows,
            confirmation_template_match_result=template_match,
            confirmation_template_mapping_result=template_mapping,
        )

    def import_workbook(self, file_path: str, workbook_type: str) -> WorkbookImportPayload:
        """Import one confirmation workbook and return normalized rows."""
        validation = self.validate_workbook(file_path, workbook_type)
        dataframe = pd.DataFrame()
        if validation.is_valid:
            dataframe = self._read_dataframe(file_path, sheet_name=validation.detected_sheet_name)
            dataframe = self.normalize_columns(dataframe)
        return self._import_normalized_dataframe(dataframe, workbook_type, validation)

    def build_match_result_for_template(
        self,
        file_path: str,
        template_name: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> ConfirmationTemplateMatchResult:
        """Diagnose the best sheet for an explicitly selected template profile."""
        profile = get_confirmation_template_profile(template_name)
        matcher = ConfirmationTemplateMatcher()
        sheet_headers = matcher.read_candidate_sheet_headers(file_path, sheet_name=sheet_name)
        best_sheet: str | None = None
        best_score: dict[str, Any] | None = None
        for candidate_sheet, headers in sheet_headers.items():
            score = matcher.score_template_profile(
                profile,
                headers,
                workbook_type=workbook_type or profile.workbook_type,
            )
            if best_score is None or (score["confidence"], score["score"]) > (
                best_score["confidence"],
                best_score["score"],
            ):
                best_sheet = candidate_sheet
                best_score = score
        if best_score is None:
            return ConfirmationTemplateMatchResult(
                matched_template_name=profile.template_name,
                workbook_type=profile.workbook_type,
                confidence=0.0,
                fallback_used=True,
                message="No readable confirmation workbook sheet matched the selected template.",
            )
        missing_required = list(best_score["missing_required_fields"])
        warnings = []
        if missing_required:
            warnings.append("Missing required fields: " + ", ".join(missing_required))
        if workbook_type and workbook_type != profile.workbook_type:
            warnings.append(
                f"Selected template workbook type '{profile.workbook_type}' differs from requested '{workbook_type}'."
            )
        return ConfirmationTemplateMatchResult(
            matched_template_name=profile.template_name,
            workbook_type=profile.workbook_type,
            confidence=float(best_score["confidence"]),
            matched_sheet_name=best_sheet,
            matched_headers=list(best_score["matched_headers"]),
            missing_required_fields=missing_required,
            unmapped_source_columns=list(best_score["unmapped_source_columns"]),
            fallback_used=bool(missing_required),
            warnings=warnings,
            message=(
                f"Selected confirmation template '{profile.template_name}' was applied."
                if not missing_required
                else "Selected confirmation template was applied, but required fields are missing."
            ),
        )

    def import_confirmation_with_template(
        self,
        file_path: str,
        template_name: str | None = None,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> WorkbookImportPayload:
        """Import a confirmation workbook using template-specific column mapping."""
        match_result = None
        selected_template = template_name
        selected_sheet = sheet_name
        if selected_template is None:
            match_result = self.diagnose_confirmation_template(
                file_path,
                workbook_type=workbook_type,
                sheet_name=sheet_name,
            )
            selected_template = match_result.matched_template_name
            selected_sheet = match_result.matched_sheet_name or sheet_name
        else:
            match_result = self.build_match_result_for_template(
                file_path,
                selected_template,
                workbook_type=workbook_type,
                sheet_name=sheet_name,
            )
            selected_sheet = sheet_name or match_result.matched_sheet_name
        if selected_template is None:
            validation = WorkbookValidationResult(
                workbook_type=workbook_type or "unknown",
                is_valid=False,
                messages=["No confirmation workbook template was selected or matched."],
            )
            summary = WorkbookImportSummary(
                workbook_type=workbook_type or "unknown",
                total_rows=0,
                imported_count=0,
                skipped_count=0,
                invalid_count=0,
                accepted_count=0,
                rejected_count=0,
                edited_count=0,
                manual_review_count=0,
                summary="Template matching failed.",
            )
            return WorkbookImportPayload(
                workbook_type or "unknown",
                validation,
                summary,
                [],
                [],
                match_result,
                None,
            )
        profile = get_confirmation_template_profile(selected_template)
        dataframe = self._read_dataframe(file_path, sheet_name=selected_sheet)
        mapping_result = self.build_template_mapping_result(dataframe, selected_template)
        validation = WorkbookValidationResult(
            workbook_type=profile.workbook_type,
            is_valid=mapping_result.status == "success",
            detected_sheet_name=selected_sheet,
            required_columns_present=[
                field for field in profile.required_target_fields if field in mapping_result.mapped_fields
            ],
            missing_required_columns=list(mapping_result.missing_required_fields),
            messages=[] if mapping_result.status == "success" else [mapping_result.message or "Template mapping failed."],
        )
        normalized_dataframe = self.dataframe_from_template_mapping(dataframe, mapping_result)
        return self._import_normalized_dataframe(
            normalized_dataframe,
            profile.workbook_type,
            validation,
            template_match=match_result,
            template_mapping=mapping_result,
        )

    def import_mapping_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "mapping_confirmation")

    def import_stg_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "stg_confirmation")

    def import_quality_rule_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "quality_rule_confirmation")

    def import_backlog_confirmation_workbook(self, file_path: str) -> WorkbookImportPayload:
        return self.import_workbook(file_path, "backlog_confirmation")


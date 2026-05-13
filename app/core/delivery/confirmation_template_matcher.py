"""Rule-based confirmation workbook template matcher."""

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.delivery.confirmation_template_loader import (
    list_enabled_confirmation_template_profiles,
    load_confirmation_template_mapping_specs,
)
from app.core.models.confirmation_template_match_result import (
    ConfirmationTemplateMatchResult,
)
from app.core.models.confirmation_template_profile import ConfirmationTemplateProfile
from app.core.normalize import clean_text
from app.core.rules.config_loader import (
    get_confirmation_workbook_diagnosis_policies_config,
)


class ConfirmationTemplateMatcher:
    """Match confirmation workbook templates using configured header aliases."""

    @staticmethod
    def _normalize_header(value: object) -> str:
        return clean_text(str(value or "")).replace(" ", "").replace("_", "").lower()

    @staticmethod
    def _read_headers_from_dataframe(dataframe: pd.DataFrame) -> list[str]:
        return [str(column).strip() for column in dataframe.columns if str(column).strip()]

    def read_candidate_sheet_headers(
        self,
        file_path: str,
        sheet_name: str | None = None,
    ) -> dict[str | None, list[str]]:
        """Read CSV headers or candidate Excel sheet headers."""
        path = Path(file_path)
        extension = path.suffix.lower().lstrip(".")
        if extension == "csv":
            return {None: self._read_headers_from_dataframe(pd.read_csv(path, nrows=0))}
        if extension not in {"xlsx", "xls"}:
            raise ValueError(f"Unsupported confirmation workbook file type: {extension or '<none>'}.")
        excel_file = pd.ExcelFile(path)
        selected_sheets = [sheet_name] if sheet_name else list(excel_file.sheet_names)
        headers: dict[str | None, list[str]] = {}
        for candidate in selected_sheets:
            if candidate not in excel_file.sheet_names:
                continue
            headers[candidate] = self._read_headers_from_dataframe(
                pd.read_excel(path, sheet_name=candidate, nrows=0)
            )
        if not headers:
            raise ValueError("No readable confirmation workbook sheet headers were found.")
        return headers

    def score_template_profile(
        self,
        profile: ConfirmationTemplateProfile,
        headers: list[str],
        workbook_type: str | None = None,
    ) -> dict[str, Any]:
        """Score one template profile against source headers."""
        specs = load_confirmation_template_mapping_specs()
        mapping_spec = specs.get(profile.mapping_spec_name)
        if mapping_spec is None:
            raise ValueError(
                f"Mapping spec '{profile.mapping_spec_name}' was not found for template '{profile.template_name}'."
            )
        policies = get_confirmation_workbook_diagnosis_policies_config().get(
            "matching_policy",
            {},
        )
        exact_score = float(policies.get("exact_header_score", 1.0))
        alias_score = float(policies.get("alias_header_score", 0.8))
        workbook_type_bonus = float(policies.get("workbook_type_bonus", 0.1))
        normalized_headers = {self._normalize_header(header): header for header in headers}
        matched_headers: list[str] = []
        matched_target_fields: list[str] = []
        score = 0.0
        target_fields = list(profile.required_target_fields) + list(profile.optional_target_fields)
        for target_field in target_fields:
            aliases = [target_field] + list(mapping_spec.get(target_field, []))
            for alias in aliases:
                normalized_alias = self._normalize_header(alias)
                if normalized_alias in normalized_headers:
                    matched_headers.append(normalized_headers[normalized_alias])
                    matched_target_fields.append(target_field)
                    score += exact_score if normalized_alias == self._normalize_header(target_field) else alias_score
                    break
        if workbook_type and workbook_type == profile.workbook_type:
            score += workbook_type_bonus
        missing_required = [
            field for field in profile.required_target_fields if field not in matched_target_fields
        ]
        mapped_headers = set(matched_headers)
        unmapped_source_columns = [header for header in headers if header not in mapped_headers]
        coverage = len(set(matched_target_fields)) / max(1, len(set(target_fields)))
        required_coverage = (
            (len(profile.required_target_fields) - len(missing_required))
            / max(1, len(profile.required_target_fields))
        )
        confidence = round(min(1.0, (coverage * 0.55) + (required_coverage * 0.45)), 2)
        return {
            "template_name": profile.template_name,
            "workbook_type": profile.workbook_type,
            "score": score,
            "confidence": confidence,
            "matched_headers": sorted(set(matched_headers)),
            "missing_required_fields": missing_required,
            "unmapped_source_columns": unmapped_source_columns,
        }

    def choose_best_template(
        self,
        headers: list[str],
        workbook_type: str | None = None,
    ) -> dict[str, Any] | None:
        """Choose the highest scoring template for one header set."""
        profiles = list_enabled_confirmation_template_profiles()
        if workbook_type:
            profiles = [profile for profile in profiles if profile.workbook_type == workbook_type]
        scored = [
            self.score_template_profile(profile, headers, workbook_type=workbook_type)
            for profile in profiles
        ]
        valid = [item for item in scored if not item["missing_required_fields"]]
        candidates = valid or scored
        if not candidates:
            return None
        return max(candidates, key=lambda item: item["score"])

    def choose_best_sheet(
        self,
        sheet_headers: dict[str | None, list[str]],
        workbook_type: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Choose the best sheet and template score together."""
        best_sheet: str | None = None
        best_score: dict[str, Any] | None = None
        for sheet, headers in sheet_headers.items():
            score = self.choose_best_template(headers, workbook_type=workbook_type)
            if score is None:
                continue
            if best_score is None or (score["confidence"], score["score"]) > (
                best_score["confidence"],
                best_score["score"],
            ):
                best_sheet = sheet
                best_score = score
        return best_sheet, best_score

    def match(
        self,
        file_path: str,
        workbook_type: str | None = None,
        sheet_name: str | None = None,
    ) -> ConfirmationTemplateMatchResult:
        """Match a confirmation workbook template from file headers."""
        sheet_headers = self.read_candidate_sheet_headers(file_path, sheet_name=sheet_name)
        matched_sheet, best_score = self.choose_best_sheet(sheet_headers, workbook_type=workbook_type)
        if best_score is None or best_score["confidence"] < 0.3:
            return ConfirmationTemplateMatchResult(
                workbook_type=workbook_type,
                confidence=0.0,
                matched_sheet_name=matched_sheet,
                fallback_used=True,
                message="No confirmation workbook template matched the provided headers.",
            )
        missing_required = list(best_score["missing_required_fields"])
        fallback = bool(missing_required)
        warnings = []
        if missing_required:
            warnings.append("Missing required fields: " + ", ".join(missing_required))
        return ConfirmationTemplateMatchResult(
            matched_template_name=str(best_score["template_name"]),
            workbook_type=str(best_score["workbook_type"]),
            confidence=float(best_score["confidence"]),
            matched_sheet_name=matched_sheet,
            matched_headers=list(best_score["matched_headers"]),
            missing_required_fields=missing_required,
            unmapped_source_columns=list(best_score["unmapped_source_columns"]),
            fallback_used=fallback,
            warnings=warnings,
            message=(
                f"Matched confirmation template '{best_score['template_name']}'."
                if not fallback
                else "A likely confirmation template was found, but required fields are missing."
            ),
        )


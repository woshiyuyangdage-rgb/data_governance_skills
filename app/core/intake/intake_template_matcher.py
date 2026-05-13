"""Rule-based metadata intake template matcher."""

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.intake.intake_profile_loader import (
    list_enabled_intake_template_profiles,
    load_intake_mapping_specs,
)
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_template_profile import IntakeTemplateProfile
from app.core.normalize import clean_text
from app.core.rules.config_loader import get_intake_diagnosis_policies_config


class IntakeTemplateMatcher:
    """Match structured metadata files to configured intake profiles."""

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
        """Read headers from CSV or candidate Excel sheets."""
        path = Path(file_path)
        extension = path.suffix.lower().lstrip(".")
        if extension == "csv":
            dataframe = pd.read_csv(path, nrows=0)
            return {None: self._read_headers_from_dataframe(dataframe)}
        if extension not in {"xlsx", "xls"}:
            raise ValueError(f"Unsupported intake file type: {extension or '<none>'}.")

        excel_file = pd.ExcelFile(path)
        selected_sheets = [sheet_name] if sheet_name else list(excel_file.sheet_names)
        headers: dict[str | None, list[str]] = {}
        for candidate in selected_sheets:
            if candidate not in excel_file.sheet_names:
                continue
            dataframe = pd.read_excel(path, sheet_name=candidate, nrows=0)
            headers[candidate] = self._read_headers_from_dataframe(dataframe)
        if not headers:
            raise ValueError("No readable Excel sheet headers were found.")
        return headers

    def score_profile_against_headers(
        self,
        profile: IntakeTemplateProfile,
        headers: list[str],
    ) -> dict[str, Any]:
        """Score one profile against headers using mapping specs."""
        specs = load_intake_mapping_specs()
        mapping_spec = specs.get(profile.mapping_spec_name)
        if mapping_spec is None:
            raise ValueError(
                f"Mapping spec '{profile.mapping_spec_name}' was not found for profile '{profile.profile_name}'."
            )
        policies = get_intake_diagnosis_policies_config().get("matching_policy", {})
        exact_score = float(policies.get("exact_header_score", 1.0))
        alias_score = float(policies.get("alias_header_score", 0.8))
        weak_score = float(policies.get("weak_header_score", 0.5))

        normalized_headers = {self._normalize_header(header): header for header in headers}
        matched_headers: list[str] = []
        matched_target_fields: list[str] = []
        score = 0.0
        target_fields = list(profile.required_target_fields) + list(profile.optional_target_fields)
        for target_field in target_fields:
            aliases = [target_field] + list(mapping_spec.get(target_field, []))
            target_matched = False
            for alias in aliases:
                normalized_alias = self._normalize_header(alias)
                if normalized_alias in normalized_headers:
                    matched_headers.append(normalized_headers[normalized_alias])
                    matched_target_fields.append(target_field)
                    score += exact_score if normalized_alias == self._normalize_header(target_field) else alias_score
                    target_matched = True
                    break
            if not target_matched:
                for normalized_header, original_header in normalized_headers.items():
                    if normalized_header and self._normalize_header(target_field) in normalized_header:
                        matched_headers.append(original_header)
                        matched_target_fields.append(target_field)
                        score += weak_score
                        break

        missing_required = [
            field for field in profile.required_target_fields if field not in matched_target_fields
        ]
        coverage = len(set(matched_target_fields)) / max(1, len(set(target_fields)))
        required_coverage = (
            (len(profile.required_target_fields) - len(missing_required))
            / max(1, len(profile.required_target_fields))
        )
        confidence = round(min(1.0, (coverage * 0.55) + (required_coverage * 0.45)), 2)
        return {
            "profile_name": profile.profile_name,
            "score": score,
            "confidence": confidence,
            "matched_headers": sorted(set(matched_headers)),
            "missing_required_fields": missing_required,
        }

    def choose_best_profile(self, headers: list[str]) -> dict[str, Any] | None:
        """Choose the highest scoring profile for one header set."""
        scored = [
            self.score_profile_against_headers(profile, headers)
            for profile in list_enabled_intake_template_profiles()
        ]
        valid = [item for item in scored if not item["missing_required_fields"]]
        candidates = valid or scored
        if not candidates:
            return None
        # Keep config order stable when simple templates tie on header overlap.
        return max(candidates, key=lambda item: item["score"])

    def choose_best_sheet(
        self,
        sheet_headers: dict[str | None, list[str]],
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Choose the best sheet and profile score together."""
        best_sheet: str | None = None
        best_score: dict[str, Any] | None = None
        for sheet, headers in sheet_headers.items():
            score = self.choose_best_profile(headers)
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
        sheet_name: str | None = None,
    ) -> IntakeMatchResult:
        """Match an intake template from a local structured metadata file."""
        sheet_headers = self.read_candidate_sheet_headers(file_path, sheet_name=sheet_name)
        matched_sheet, best_score = self.choose_best_sheet(sheet_headers)
        if best_score is None or best_score["confidence"] < 0.3:
            return IntakeMatchResult(
                confidence=0.0,
                matched_sheet_name=matched_sheet,
                fallback_used=True,
                message="No intake template profile matched the provided headers.",
            )
        missing_required = list(best_score["missing_required_fields"])
        fallback = bool(missing_required)
        warnings = []
        if missing_required:
            warnings.append(
                "Missing required target fields: " + ", ".join(missing_required)
            )
        return IntakeMatchResult(
            matched_profile_name=str(best_score["profile_name"]),
            confidence=float(best_score["confidence"]),
            matched_sheet_name=matched_sheet,
            matched_headers=list(best_score["matched_headers"]),
            missing_required_fields=missing_required,
            warnings=warnings,
            fallback_used=fallback,
            message=(
                f"Matched intake profile '{best_score['profile_name']}'."
                if not fallback
                else "A likely intake profile was found, but required fields are missing."
            ),
        )


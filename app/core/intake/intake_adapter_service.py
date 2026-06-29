"""Normalize enterprise metadata intake files into standard metadata records."""

from pathlib import Path
from typing import Any

import pandas as pd

from app.core.intake.intake_profile_loader import (
    get_intake_template_profile,
    load_intake_mapping_specs,
)
from app.core.intake.intake_template_matcher import IntakeTemplateMatcher
from app.core.models.intake_mapping_result import IntakeMappingResult
from app.core.models.intake_match_result import IntakeMatchResult
from app.core.models.intake_normalization_result import IntakeNormalizationResult
from app.core.models.table_meta import TableMeta
from app.core.normalize import clean_text
from app.core.parser._shared import dataframe_to_tables, normalize_nullable
from app.core.rules.config_loader import get_intake_diagnosis_policies_config


class IntakeAdapterService:
    """Diagnose and normalize structured enterprise metadata intake files."""

    STANDARD_FIELDS = [
        "table_name",
        "table_name_cn",
        "table_description",
        "schema_name",
        "system_name",
        "field_name",
        "field_name_cn",
        "field_description",
        "data_type",
        "nullable",
    ]

    @staticmethod
    def _normalize_header(value: object) -> str:
        return clean_text(str(value or "")).replace(" ", "").replace("_", "").lower()

    @staticmethod
    def _clean_value(value: object) -> object | None:
        if value is None or pd.isna(value):
            return None
        text = str(value).strip()
        return text or None

    def diagnose_intake_template(
        self,
        file_path: str,
        sheet_name: str | None = None,
    ) -> IntakeMatchResult:
        """Diagnose the best intake template for a file."""
        return IntakeTemplateMatcher().match(file_path, sheet_name=sheet_name)

    def _read_dataframe(self, file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
        path = Path(file_path)
        extension = path.suffix.lower()
        if extension == ".csv":
            return pd.read_csv(path)
        if extension in {".xlsx", ".xls"}:
            return pd.read_excel(path, sheet_name=sheet_name or 0)
        raise ValueError(f"Unsupported intake file type '{extension or '<none>'}'.")

    def _build_column_mapping(
        self,
        profile_name: str,
        source_columns: list[str],
    ) -> IntakeMappingResult:
        profile = get_intake_template_profile(profile_name)
        mapping_specs = load_intake_mapping_specs()
        spec = mapping_specs.get(profile.mapping_spec_name)
        if spec is None:
            raise ValueError(f"Mapping spec '{profile.mapping_spec_name}' was not found.")

        normalized_source = {
            self._normalize_header(column): column for column in source_columns
        }
        mapped_fields: dict[str, str] = {}
        for target_field in self.STANDARD_FIELDS:
            aliases = [target_field] + list(spec.get(target_field, []))
            for alias in aliases:
                normalized_alias = self._normalize_header(alias)
                if normalized_alias in normalized_source:
                    mapped_fields[target_field] = normalized_source[normalized_alias]
                    break

        mapped_source_columns = set(mapped_fields.values())
        missing_required = [
            field for field in profile.required_target_fields if field not in mapped_fields
        ]
        unmapped_source_columns = [
            column for column in source_columns if column not in mapped_source_columns
        ]
        status = "success" if not missing_required else "failed"
        return IntakeMappingResult(
            profile_name=profile.profile_name,
            source_columns=source_columns,
            mapped_fields=mapped_fields,
            unmapped_source_columns=unmapped_source_columns,
            missing_required_fields=missing_required,
            status=status,
            message=(
                "Source columns mapped to normalized metadata fields."
                if status == "success"
                else "Required target fields are missing: " + ", ".join(missing_required)
            ),
        )

    def _normalize_dataframe(
        self,
        dataframe: pd.DataFrame,
        mapping_result: IntakeMappingResult,
    ) -> pd.DataFrame:
        records: list[dict[str, Any]] = []
        policies = get_intake_diagnosis_policies_config().get("diagnosis_policy", {})
        normalize_nullable_values = bool(policies.get("normalize_boolean_nullable", True))
        for row in dataframe.to_dict(orient="records"):
            normalized_row: dict[str, Any] = {}
            for target_field in self.STANDARD_FIELDS:
                source_column = mapping_result.mapped_fields.get(target_field)
                value = row.get(source_column) if source_column else None
                normalized_row[target_field] = self._clean_value(value)
            if normalize_nullable_values:
                normalized_row["nullable"] = normalize_nullable(normalized_row.get("nullable"))
            records.append(normalized_row)
        return pd.DataFrame(records, columns=self.STANDARD_FIELDS)

    def normalize_metadata_input(
        self,
        file_path: str,
        profile_name: str | None = None,
        sheet_name: str | None = None,
    ) -> IntakeNormalizationResult:
        """Normalize an intake file into standard metadata records."""
        match_result = None
        selected_profile = profile_name
        selected_sheet = sheet_name
        if selected_profile is None:
            match_result = self.diagnose_intake_template(file_path, sheet_name=sheet_name)
            selected_profile = match_result.matched_profile_name
            selected_sheet = match_result.matched_sheet_name or sheet_name
        if selected_profile is None:
            mapping_result = IntakeMappingResult(
                profile_name="unknown",
                status="failed",
                message="No intake profile was selected or matched.",
            )
            return IntakeNormalizationResult(
                profile_name="unknown",
                row_count=0,
                table_count=0,
                normalized_records=[],
                mapping_result=mapping_result,
                status="failed",
                message=mapping_result.message,
            )

        dataframe = self._read_dataframe(file_path, sheet_name=selected_sheet)
        dataframe = dataframe.dropna(how="all")
        source_columns = [str(column).strip() for column in dataframe.columns]
        mapping_result = self._build_column_mapping(selected_profile, source_columns)
        if mapping_result.status != "success":
            return IntakeNormalizationResult(
                profile_name=selected_profile,
                row_count=int(len(dataframe)),
                table_count=0,
                normalized_records=[],
                mapping_result=mapping_result,
                status="failed",
                message=mapping_result.message,
            )

        normalized_dataframe = self._normalize_dataframe(dataframe, mapping_result)
        normalized_records = normalized_dataframe.where(pd.notna(normalized_dataframe), None).to_dict(orient="records")
        tables = dataframe_to_tables(normalized_dataframe)
        result = IntakeNormalizationResult(
            profile_name=selected_profile,
            row_count=len(normalized_records),
            table_count=len(tables),
            normalized_records=normalized_records,
            mapping_result=mapping_result,
            status="success",
            message="Metadata intake file was normalized successfully.",
        )
        if match_result:
            result.message = f"{result.message} {match_result.message or ''}".strip()
        return result

    def load_tables(
        self,
        file_path: str,
        profile_name: str | None = None,
        sheet_name: str | None = None,
    ) -> tuple[list[TableMeta], IntakeMatchResult | None, IntakeNormalizationResult]:
        """Normalize and convert an intake file to existing table models."""
        match_result = None
        selected_profile = profile_name
        selected_sheet = sheet_name
        if selected_profile is None:
            match_result = self.diagnose_intake_template(file_path, sheet_name=sheet_name)
            selected_profile = match_result.matched_profile_name
            selected_sheet = match_result.matched_sheet_name or sheet_name
        normalization = self.normalize_metadata_input(
            file_path,
            profile_name=selected_profile,
            sheet_name=selected_sheet,
        )
        if normalization.status != "success":
            return [], match_result, normalization
        tables = dataframe_to_tables(pd.DataFrame(normalization.normalized_records))
        return tables, match_result, normalization


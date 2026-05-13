"""Rule-based enterprise delivery layout adapter."""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.core.delivery.delivery_template_loader import (
    get_delivery_template_profile,
    load_delivery_bundle_variants,
    load_delivery_layout_specs,
)
from app.core.models.delivery_bundle_variant_result import DeliveryBundleVariantResult
from app.core.models.delivery_layout_result import DeliveryLayoutResult


@dataclass
class AdaptedWorkbookLayout:
    """Adapted workbook dataframe and layout metadata."""

    dataframe: pd.DataFrame
    sheet_name: str
    include_instruction_sheet: bool
    include_summary_sheet: bool
    result: DeliveryLayoutResult


class EnterpriseDeliveryAdapter:
    """Apply configured enterprise delivery templates to local outputs."""

    def __init__(self) -> None:
        self.layout_specs = load_delivery_layout_specs()
        self.bundle_variants = load_delivery_bundle_variants()

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return str(value)
        return value

    def adapt_dataframe(
        self,
        dataframe: pd.DataFrame,
        template_name: str,
    ) -> AdaptedWorkbookLayout:
        """Apply one delivery template profile and layout spec to a dataframe."""
        profile = get_delivery_template_profile(template_name)
        spec = self.layout_specs.get(profile.layout_spec_name)
        if not isinstance(spec, dict) or not spec:
            raise ValueError(
                f"Layout spec '{profile.layout_spec_name}' was not found for delivery template '{template_name}'."
            )
        column_order = [str(column) for column in spec.get("column_order", [])]
        display_columns = {
            str(key): str(value)
            for key, value in dict(spec.get("display_columns", {})).items()
        }
        extra_columns = dict(spec.get("extra_columns", {}))
        adapted_df = dataframe.copy()
        extra_columns_added: list[str] = []
        for column, default_value in extra_columns.items():
            column_name = str(column)
            if column_name not in adapted_df.columns:
                adapted_df[column_name] = default_value
                extra_columns_added.append(column_name)
        applied_columns = list(column_order)
        for column in extra_columns:
            column_name = str(column)
            if column_name not in applied_columns:
                applied_columns.append(column_name)
        if not applied_columns:
            applied_columns = [str(column) for column in adapted_df.columns]
        for column in applied_columns:
            if column not in adapted_df.columns:
                adapted_df[column] = None
        adapted_df = adapted_df[applied_columns].map(self._stringify)
        adapted_df = adapted_df.rename(
            columns={column: display_columns.get(column, column) for column in applied_columns}
        )
        sheet_name = str(spec.get("sheet_name") or profile.target_artifact_type)
        result = DeliveryLayoutResult(
            template_name=profile.template_name,
            layout_spec_name=profile.layout_spec_name,
            target_artifact_type=profile.target_artifact_type,
            applied_sheet_name=sheet_name,
            applied_columns=list(adapted_df.columns),
            extra_columns_added=extra_columns_added,
            status="success",
            message=f"Delivery layout '{profile.layout_spec_name}' applied.",
        )
        return AdaptedWorkbookLayout(
            dataframe=adapted_df,
            sheet_name=sheet_name,
            include_instruction_sheet=profile.include_instruction_sheet,
            include_summary_sheet=profile.include_summary_sheet,
            result=result,
        )

    def adapt_mapping_confirmation_workbook(
        self,
        dataframe: pd.DataFrame,
        template_name: str = "business_mapping_delivery_template",
    ) -> AdaptedWorkbookLayout:
        """Adapt a mapping confirmation workbook dataframe."""
        return self.adapt_dataframe(dataframe, template_name)

    def adapt_stg_confirmation_workbook(
        self,
        dataframe: pd.DataFrame,
        template_name: str = "architecture_stg_delivery_template",
    ) -> AdaptedWorkbookLayout:
        """Adapt an STG confirmation workbook dataframe."""
        return self.adapt_dataframe(dataframe, template_name)

    def adapt_quality_rule_confirmation_workbook(
        self,
        dataframe: pd.DataFrame,
        template_name: str = "quality_rule_review_delivery_template",
    ) -> AdaptedWorkbookLayout:
        """Adapt a quality rule confirmation workbook dataframe."""
        return self.adapt_dataframe(dataframe, template_name)

    def adapt_backlog_delivery_workbook(
        self,
        dataframe: pd.DataFrame,
        template_name: str = "governance_backlog_delivery_template",
    ) -> AdaptedWorkbookLayout:
        """Adapt a governance backlog delivery workbook dataframe."""
        return self.adapt_dataframe(dataframe, template_name)

    def adapt_governance_delivery_package(
        self,
        generated_files: dict[str, str],
        variant_name: str = "standard_delivery_bundle",
    ) -> DeliveryBundleVariantResult:
        """Filter generated package files according to one bundle variant."""
        variant = self.bundle_variants.get(variant_name)
        if not isinstance(variant, dict):
            raise ValueError(f"Delivery bundle variant '{variant_name}' was not found.")
        included_outputs = [str(item) for item in variant.get("included_outputs", [])]
        adapted_files: dict[str, str] = {}
        for output_name in included_outputs:
            if output_name == "governance_delivery_manifest" and "package_manifest" in generated_files:
                adapted_files[output_name] = generated_files["package_manifest"]
            elif output_name == "backlog_delivery_workbook" and "backlog_workbook" in generated_files:
                adapted_files[output_name] = generated_files["backlog_workbook"]
            elif output_name in generated_files:
                adapted_files[output_name] = generated_files[output_name]
        status = "success" if adapted_files else "empty"
        return DeliveryBundleVariantResult(
            variant_name=variant_name,
            included_outputs=included_outputs,
            generated_files=adapted_files,
            status=status,
            message=(
                f"Delivery bundle variant '{variant_name}' applied with {len(adapted_files)} generated files."
            ),
        )


# TODO: extend this adapter with department-specific delivery templates, workbook style presets, and external delivery adapters.

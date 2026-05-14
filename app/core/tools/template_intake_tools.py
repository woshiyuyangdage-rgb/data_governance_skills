"""Domain pack, project template, and metadata intake tool handlers."""

from app.core.delivery.delivery_template_loader import (
    list_enabled_delivery_bundle_variants,
    list_enabled_delivery_template_profiles,
)
from app.core.domain.domain_pack_loader import list_enabled_domain_packs
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.intake.intake_adapter_service import IntakeAdapterService
from app.core.models.tool_call_response import ToolCallResponse
from app.core.templates.project_template_loader import list_enabled_project_templates
from app.core.templates.project_template_service import ProjectTemplateService


class TemplateIntakeToolMixin:
    """Tool handlers for domain packs, project templates, and intake adapters."""

    def list_domain_governance_packs(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List enabled domain governance packs."""
        tool_name = "list_domain_governance_packs"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            packs = [pack.model_dump() for pack in list_enabled_domain_packs()]
            trace = self._finish_trace(
                trace,
                "success",
                f"Listed {len(packs)} domain governance packs.",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Domain governance packs listed.",
                {"packs": packs},
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def list_project_templates(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List enabled project templates."""
        tool_name = "list_project_templates"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            templates = [
                template.model_dump() for template in list_enabled_project_templates()
            ]
            trace = self._finish_trace(
                trace,
                "success",
                f"Listed {len(templates)} project templates.",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Project templates listed.",
                {"templates": templates},
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def list_delivery_template_profiles(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List enabled enterprise delivery templates and bundle variants."""
        tool_name = "list_delivery_template_profiles"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            profiles = [
                profile.model_dump()
                for profile in list_enabled_delivery_template_profiles()
            ]
            variants = list_enabled_delivery_bundle_variants()
            trace = self._finish_trace(
                trace,
                "success",
                f"Listed {len(profiles)} delivery templates and {len(variants)} bundle variants.",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Delivery template profiles listed.",
                {
                    "profiles": profiles,
                    "bundle_variants": variants,
                },
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def match_domain_governance_pack(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Match a domain governance pack from text."""
        tool_name = "match_domain_governance_pack"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            match = DomainPackMatcher().match_domain_pack_from_text(
                self._require_text(arguments)
            )
            trace = self._finish_trace(
                trace,
                "success",
                match.message or "Domain governance pack matched.",
                domain_pack_name=match.matched_pack_name,
                domain_pack_match_confidence=match.confidence,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                trace.message or "Matched.",
                match.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def run_project_template(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Run a project template with optional domain pack override."""
        tool_name = "run_project_template"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name="run_project_template",
        )
        try:
            template_name = self._optional_string(arguments, "template_name")
            file_path = self._optional_string(arguments, "file_path")
            if not template_name or not file_path:
                raise ValueError(
                    "Arguments 'template_name' and 'file_path' are required."
                )
            result = ProjectTemplateService().run_project_template(
                template_name=template_name,
                file_path=file_path,
                domain_pack_name=self._optional_string(arguments, "domain_pack_name"),
                output_dir=self._optional_string(arguments, "output_dir"),
            )
            template_result = result.project_template_result
            applied_outputs: list[str] = []
            selected_pack = None
            if template_result is not None:
                selected_pack = template_result.selected_domain_pack
                outputs = template_result.applied_defaults.get("default_outputs", [])
                if isinstance(outputs, list):
                    applied_outputs = [str(item) for item in outputs]
            match_confidence = (
                result.domain_pack_match.confidence
                if result.domain_pack_match
                else None
            )
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                domain_pack_name=selected_pack,
                template_name=template_name,
                domain_pack_match_confidence=match_confidence,
                applied_delivery_outputs=applied_outputs,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                str(exc),
                template_name=self._optional_string(arguments, "template_name"),
            )
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def diagnose_metadata_intake_template(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Diagnose a structured metadata intake template."""
        tool_name = "diagnose_metadata_intake_template"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = IntakeAdapterService().diagnose_intake_template(
                file_path,
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            trace = self._finish_trace(
                trace,
                "success",
                result.message or "Metadata intake template diagnosed.",
                intake_profile_name=result.matched_profile_name,
                intake_match_confidence=result.confidence,
                matched_sheet_name=result.matched_sheet_name,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                trace.message or "Diagnosed.",
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def normalize_metadata_input(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Normalize an enterprise metadata intake file."""
        tool_name = "normalize_metadata_input"
        trace = self._start_trace(tool_name=tool_name, arguments=arguments)
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            result = IntakeAdapterService().normalize_metadata_input(
                file_path,
                profile_name=self._optional_string(arguments, "intake_profile_name"),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            unmapped_count = (
                len(result.mapping_result.unmapped_source_columns)
                if result.mapping_result is not None
                else None
            )
            trace = self._finish_trace(
                trace,
                result.status,
                result.message or "Metadata input normalized.",
                intake_profile_name=result.profile_name,
                unmapped_source_column_count=unmapped_count,
                normalization_row_count=result.row_count,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message or "Normalized.",
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

    def run_governance_with_intake_profile(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Normalize intake metadata and run a governance workflow."""
        tool_name = "run_governance_with_intake_profile"
        profile_name = (
            self._optional_string(arguments, "profile_name")
            or "metadata_diagnosis_only"
        )
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            profile_name=profile_name,
        )
        try:
            file_path = self._optional_string(arguments, "file_path")
            if not file_path:
                raise ValueError("Argument 'file_path' is required.")
            from app.core.orchestrator.workflow_engine import WorkflowEngine

            result = WorkflowEngine().run_governance_with_intake_profile(
                file_path,
                profile_name=profile_name,
                intake_profile_name=self._optional_string(
                    arguments,
                    "intake_profile_name",
                ),
                sheet_name=self._optional_string(arguments, "sheet_name"),
            )
            mapping = result.intake_mapping_result
            normalization = result.intake_normalization_result
            match = result.intake_match_result
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                intake_profile_name=normalization.profile_name if normalization else None,
                intake_match_confidence=match.confidence if match else None,
                matched_sheet_name=match.matched_sheet_name if match else None,
                unmapped_source_column_count=(
                    len(mapping.unmapped_source_columns) if mapping else None
                ),
                normalization_row_count=normalization.row_count if normalization else None,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(trace, "failed", str(exc))
            return self._build_tool_response(tool_name, "failed", str(exc), None, trace)

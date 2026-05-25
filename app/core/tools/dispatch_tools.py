"""Tool dispatch and registration helpers for the governance executor."""

from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.tool_definition import ToolDefinition


class ToolDispatchMixin:
    """Dispatch enabled tool definitions to executor handler methods."""

    def build_unavailable_tool_response(
        self,
        tool_name: str,
        arguments: dict[str, object],
        message: str,
    ) -> ToolCallResponse:
        """Return a traced failure response for missing or disabled tools."""
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            raw_text=self._optional_string(arguments, "text"),
            profile_name=self._optional_string(arguments, "profile_name"),
        )
        trace = self._finish_trace(trace, "failed", message)
        return self._build_tool_response(tool_name, "failed", message, None, trace)

    def call_registered_tool(
        self,
        tool_definition: ToolDefinition,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Dispatch one enabled tool definition to its bound executor method."""
        handler_map = self.get_registered_handlers()
        handler = handler_map.get(tool_definition.handler)
        if handler is None:
            return self.build_unavailable_tool_response(
                tool_definition.name,
                arguments,
                f"Tool handler '{tool_definition.handler}' is not registered.",
            )
        return handler(arguments)

    def get_registered_handlers(self):
        """Return registered tool handler bindings."""
        handler_map = {
            "governance_tool_executor.run_governance_profile": self.run_governance_profile,
            "governance_tool_executor.recommend_quality_rules": self.recommend_quality_rules,
            "governance_tool_executor.recommend_quality_intelligence": self.recommend_quality_intelligence,
            "governance_tool_executor.review_quality_rules": self.review_quality_rules,
            "governance_tool_executor.batch_review_quality_rules": self.batch_review_quality_rules,
            "governance_tool_executor.export_confirmed_quality_rules": self.export_confirmed_quality_rules,
            "governance_tool_executor.build_execution_ready_package": self.build_execution_ready_package,
            "governance_tool_executor.export_execution_ready_package": self.export_execution_ready_package,
            "governance_tool_executor.assess_rag_quality": self.assess_rag_quality,
            "governance_tool_executor.assess_governance_readiness": self.assess_governance_readiness,
            "governance_tool_executor.build_governance_work_package": self.build_governance_work_package,
            "governance_tool_executor.build_governance_backlog": self.build_governance_backlog,
            "governance_tool_executor.update_governance_backlog_status": self.update_governance_backlog_status,
            "governance_tool_executor.list_governance_backlog_items": self.list_governance_backlog_items,
            "governance_tool_executor.assess_governance_portfolio": self.assess_governance_portfolio,
            "governance_tool_executor.generate_progress_snapshot": self.generate_progress_snapshot,
            "governance_tool_executor.list_governance_progress_snapshots": self.list_governance_progress_snapshots,
            "governance_tool_executor.interpret_governance_intent": self.interpret_governance_intent,
            "governance_tool_executor.preview_agent_plan": self.preview_agent_plan,
            "governance_tool_executor.run_agent_task": self.run_agent_task,
            "governance_tool_executor.resolve_governance_context": self.resolve_governance_context,
            "governance_tool_executor.export_governance_reports": self.export_governance_reports,
            "governance_tool_executor.export_confirmation_workbooks": self.export_confirmation_workbooks,
            "governance_tool_executor.build_governance_delivery_package": self.build_governance_delivery_package,
            "governance_tool_executor.run_batch_governance": self.run_batch_governance,
            "governance_tool_executor.run_incremental_rerun": self.run_incremental_rerun,
            "governance_tool_executor.compare_governance_snapshots": self.compare_governance_snapshots,
            "governance_tool_executor.import_confirmation_workbook": self.import_confirmation_workbook,
            "governance_tool_executor.import_confirmation_and_rerun": self.import_confirmation_and_rerun,
            "governance_tool_executor.list_domain_governance_packs": self.list_domain_governance_packs,
            "governance_tool_executor.list_project_templates": self.list_project_templates,
            "governance_tool_executor.list_delivery_template_profiles": self.list_delivery_template_profiles,
            "governance_tool_executor.match_domain_governance_pack": self.match_domain_governance_pack,
            "governance_tool_executor.run_project_template": self.run_project_template,
            "governance_tool_executor.diagnose_metadata_intake_template": self.diagnose_metadata_intake_template,
            "governance_tool_executor.normalize_metadata_input": self.normalize_metadata_input,
            "governance_tool_executor.run_governance_with_intake_profile": self.run_governance_with_intake_profile,
            "governance_tool_executor.diagnose_confirmation_template": self.diagnose_confirmation_template,
            "governance_tool_executor.import_confirmation_with_template": self.import_confirmation_with_template,
            "governance_tool_executor.list_config_assets": self.list_config_assets,
            "governance_tool_executor.get_config_asset": self.get_config_asset,
            "governance_tool_executor.validate_config_asset": self.validate_config_asset,
            "governance_tool_executor.save_config_asset": self.save_config_asset,
            "governance_tool_executor.publish_config_asset": self.publish_config_asset,
        }
        return handler_map

    def list_registered_handler_names(self) -> set[str]:
        """Return registered tool handler names."""
        return set(self.get_registered_handlers().keys())

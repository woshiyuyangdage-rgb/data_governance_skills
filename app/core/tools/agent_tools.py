"""Agent shell and intent tool handlers for the governance executor."""

from app.core.intent.intent_task_service import interpret_and_build_request
from app.core.models.tool_call_response import ToolCallResponse


class AgentToolMixin:
    """Tool handlers for intent interpretation and agent shell flows."""

    def interpret_governance_intent(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Interpret natural-language intent without executing it."""
        tool_name = "interpret_governance_intent"
        text = self._require_text(arguments)
        file_path = self._optional_string(arguments, "file_path")
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            raw_text=text,
        )
        try:
            response = interpret_and_build_request(text=text, file_path=file_path)
            trace.profile_name = response.task_request.profile_name
            trace = self._finish_trace(
                trace,
                "success",
                "Governance intent was interpreted successfully.",
                notes=["Interpretation only. No workflow execution was triggered."],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Governance intent was interpreted successfully.",
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to interpret governance intent: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to interpret governance intent.",
                None,
                trace,
            )

    def preview_agent_plan(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Preview an agent plan without executing it."""
        tool_name = "preview_agent_plan"
        text = self._require_text(arguments)
        file_path = self._optional_string(arguments, "file_path")
        session_id = self._optional_string(arguments, "session_id")
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=session_id,
            raw_text=text,
        )
        try:
            response = self.agent_shell_service.interpret_to_plan(
                text=text,
                file_path=file_path,
                session_id=session_id,
            )
            trace.session_id = response.session_id
            trace.profile_name = response.task_request.profile_name
            trace = self._finish_trace(
                trace,
                response.status,
                response.message,
                stages_executed=self._extract_stages(response),
                resolved_context_summary=self._summarize_resolved_context(response),
                notes=self._collect_notes_from_agent_result(response),
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                response.message,
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to preview agent plan: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to preview agent plan.",
                None,
                trace,
            )

    def run_agent_task(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Interpret, plan, and conditionally execute through the agent shell."""
        tool_name = "run_agent_task"
        text = self._require_text(arguments)
        file_path = self._optional_string(arguments, "file_path")
        session_id = self._optional_string(arguments, "session_id")
        force_run = bool(arguments.get("force_run", False))
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=session_id,
            raw_text=text,
        )
        try:
            response = self.agent_shell_service.confirm_and_run(
                text=text,
                file_path=file_path,
                session_id=session_id,
                force_run=force_run,
            )
            trace.session_id = response.session_id
            trace.profile_name = response.task_request.profile_name
            trace = self._finish_trace(
                trace,
                response.status,
                response.message,
                stages_executed=self._extract_stages(response),
                resolved_context_summary=self._summarize_resolved_context(response),
                exported_files=self._extract_exported_files(response),
                review_summary=self._extract_review_summary(response),
                notes=self._collect_notes_from_agent_result(response),
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                response.message,
                response.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to run agent task: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to run agent task.",
                None,
                trace,
            )

    def resolve_governance_context(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Resolve session context and preview the resulting plan."""
        tool_name = "resolve_governance_context"
        text = self._require_text(arguments)
        file_path = self._optional_string(arguments, "file_path")
        session_id = self._optional_string(arguments, "session_id")
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=session_id,
            raw_text=text,
        )
        try:
            response = self.agent_shell_service.interpret_to_plan(
                text=text,
                file_path=file_path,
                session_id=session_id,
            )
            trace.session_id = response.session_id
            trace.profile_name = response.task_request.profile_name
            result_payload = {
                "interpreted_intent": response.interpreted_intent.model_dump(),
                "task_request": response.task_request.model_dump(),
                "resolved_context": (
                    response.resolved_context.model_dump()
                    if response.resolved_context is not None
                    else None
                ),
                "execution_plan": response.execution_plan.model_dump(),
                "resolution_applied": response.resolution_applied,
            }
            trace = self._finish_trace(
                trace,
                response.status,
                "Governance context was resolved successfully.",
                stages_executed=self._extract_stages(response),
                resolved_context_summary=self._summarize_resolved_context(response),
                notes=self._collect_notes_from_agent_result(response),
            )
            return self._build_tool_response(
                tool_name,
                response.status,
                "Governance context was resolved successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to resolve governance context: {exc}",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to resolve governance context.",
                None,
                trace,
            )

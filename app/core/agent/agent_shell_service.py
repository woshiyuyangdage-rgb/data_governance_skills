"""Lightweight agent shell service for preview, validation, and controlled execution."""

from app.core.context.context_resolver import ContextResolver
from app.core.agent.execution_planner import ExecutionPlanner
from app.core.agent.session_store import (
    append_plan_to_session,
    append_request_to_session,
    create_session,
    get_session,
    save_session,
    set_last_exported_files,
    set_last_task_context,
    set_last_tool_response,
)
from app.core.agent.tool_intent_resolver import AgentToolIntent, resolve_agent_tool_intent
from app.core.intent.intent_interpreter import IntentInterpreter
from app.core.models.agent_shell_result import AgentShellResult
from app.core.models.execution_plan import ExecutionPlan
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.interpreted_intent import InterpretedIntent
from app.core.models.parameter_resolution_result import ParameterResolutionResult
from app.core.models.tool_call_request import ToolCallRequest
from app.core.orchestrator.task_service import run_governance_task


class AgentShellService:
    """Preview and execute governance tasks with simple session-aware control."""

    def __init__(self) -> None:
        self.interpreter = IntentInterpreter()
        self.context_resolver = ContextResolver()
        self.planner = ExecutionPlanner()

    @staticmethod
    def _build_direct_intent(task_request: GovernanceTaskRequest) -> InterpretedIntent:
        return InterpretedIntent(
            raw_text="direct_task_request",
            matched_intent_name="direct_task_request",
            matched_profile_name=task_request.profile_name,
            confidence=1.0,
            matched_keywords=[],
            inferred_parameters={},
            fallback_used=False,
            message=(
                f"Built execution plan directly from task request profile "
                f"'{task_request.profile_name}'."
            ),
        )

    @staticmethod
    def _ensure_session(session_id: str | None) -> str:
        if session_id:
            existing = get_session(session_id)
            if existing is not None:
                return existing.session_id
            return create_session(session_id).session_id
        return create_session().session_id

    @staticmethod
    def _build_tool_task_request(tool_intent: AgentToolIntent) -> GovernanceTaskRequest:
        return GovernanceTaskRequest(
            profile_name=f"tool:{tool_intent.tool_name}",
        )

    @staticmethod
    def _build_tool_intent(
        text: str,
        tool_intent: AgentToolIntent,
    ) -> InterpretedIntent:
        return InterpretedIntent(
            raw_text=text,
            matched_intent_name=f"tool:{tool_intent.tool_name}",
            matched_profile_name=f"tool:{tool_intent.tool_name}",
            confidence=0.95,
            matched_keywords=list(tool_intent.matched_keywords),
            inferred_parameters={
                "tool_name": tool_intent.tool_name,
                "tool_arguments": dict(tool_intent.arguments),
            },
            fallback_used=False,
            match_source="local_tool_intent",
            message=(
                f"Matched local maintenance tool '{tool_intent.tool_name}'."
            ),
        )

    @staticmethod
    def _build_tool_plan(
        text: str,
        tool_intent: AgentToolIntent,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            raw_text=text,
            plan_type="tool",
            profile_name=f"tool:{tool_intent.tool_name}",
            tool_name=tool_intent.tool_name,
            tool_arguments=dict(tool_intent.arguments),
            stages=[tool_intent.tool_name],
            requires_confirmation=tool_intent.requires_confirmation,
            validation_passed=True,
            validation_messages=[],
            suggested_output_mode="tool_call",
            summary=tool_intent.summary,
        )

    def _try_tool_plan(
        self,
        text: str,
        session_id: str | None = None,
    ) -> AgentShellResult | None:
        """Return a previewable tool-call plan for supported maintenance requests."""
        tool_intent = resolve_agent_tool_intent(text)
        if tool_intent is None:
            return None

        resolved_session_id = self._ensure_session(session_id)
        interpreted_intent = self._build_tool_intent(text, tool_intent)
        task_request = self._build_tool_task_request(tool_intent)
        execution_plan = self._build_tool_plan(text, tool_intent)

        append_request_to_session(resolved_session_id, text)
        session = append_plan_to_session(resolved_session_id, execution_plan)
        session.last_task_request = task_request
        session.last_task_response = None
        save_session(session)

        return AgentShellResult(
            interpreted_intent=interpreted_intent,
            task_request=task_request,
            execution_plan=execution_plan,
            task_response=None,
            tool_response=None,
            session_id=resolved_session_id,
            status="interpreted_only",
            message="Tool call plan preview was generated successfully.",
        )

    def _prepare_plan_inputs(
        self,
        text: str,
        file_path: str | None = None,
        session_id: str | None = None,
    ) -> tuple[str, InterpretedIntent, ParameterResolutionResult]:
        """Interpret task text and resolve session-based execution context."""
        resolved_session_id = self._ensure_session(session_id)
        interpreted_intent = self.interpreter.interpret(text=text, file_path=file_path)
        task_request = self.interpreter.build_task_request(
            interpreted_intent,
            file_path=file_path,
        )
        resolution_result = self.context_resolver.resolve(
            raw_text=text,
            task_request=task_request,
            session_id=resolved_session_id,
        )
        return resolved_session_id, interpreted_intent, resolution_result

    def interpret_to_plan(
        self,
        text: str,
        file_path: str | None = None,
        session_id: str | None = None,
    ) -> AgentShellResult:
        """Interpret a natural-language request and return a previewable plan."""
        tool_plan = self._try_tool_plan(text, session_id=session_id)
        if tool_plan is not None:
            return tool_plan

        (
            resolved_session_id,
            interpreted_intent,
            resolution_result,
        ) = self._prepare_plan_inputs(
            text=text,
            file_path=file_path,
            session_id=session_id,
        )
        task_request = resolution_result.resolved_task_request
        execution_plan = self.planner.build_plan(
            interpreted_intent,
            task_request,
            resolution_result.resolved_context,
        )

        append_request_to_session(resolved_session_id, text)
        session = append_plan_to_session(resolved_session_id, execution_plan)
        session.last_task_request = task_request
        session.last_task_response = None
        save_session(session)

        status = "interpreted_only"
        message = "Plan preview was generated successfully."
        if not execution_plan.validation_passed:
            status = "validation_failed"
            message = (
                "Plan preview was generated, but required parameters are still "
                "missing or ambiguous."
            )

        return AgentShellResult(
            interpreted_intent=interpreted_intent,
            task_request=task_request,
            execution_plan=execution_plan,
            resolved_context=resolution_result.resolved_context,
            resolution_applied=resolution_result.resolution_applied,
            task_response=None,
            session_id=resolved_session_id,
            status=status,
            message=message,
        )

    def confirm_and_run(
        self,
        text: str,
        file_path: str | None = None,
        session_id: str | None = None,
        force_run: bool = False,
    ) -> AgentShellResult:
        """Interpret, plan, validate, and execute only when policy allows."""
        preview_result = self.interpret_to_plan(
            text=text,
            file_path=file_path,
            session_id=session_id,
        )

        if not preview_result.execution_plan.validation_passed:
            preview_result.status = "validation_failed"
            if (
                preview_result.resolved_context is not None
                and preview_result.resolved_context.ambiguity_detected
            ):
                preview_result.message = (
                    "Execution was blocked because context resolution found multiple "
                    "candidate parameters that still need user confirmation."
                )
            else:
                preview_result.message = (
                    "Execution was blocked because plan validation failed."
            )
            return preview_result

        if preview_result.execution_plan.plan_type == "tool":
            if preview_result.execution_plan.requires_confirmation and not force_run:
                preview_result.status = "preview_requires_confirmation"
                preview_result.message = (
                    "Tool call plan preview requires confirmation before execution."
                )
                return preview_result

            tool_name = preview_result.execution_plan.tool_name
            if not tool_name:
                preview_result.status = "validation_failed"
                preview_result.message = "Execution was blocked because tool_name is missing."
                return preview_result
            from app.core.tools.tool_service import call_tool

            tool_arguments = dict(preview_result.execution_plan.tool_arguments)
            if preview_result.session_id and "session_id" not in tool_arguments:
                tool_arguments["session_id"] = preview_result.session_id
            tool_response = call_tool(
                ToolCallRequest(
                    tool_name=tool_name,
                    arguments=tool_arguments,
                )
            )
            preview_result.tool_response = tool_response
            if preview_result.session_id:
                set_last_tool_response(preview_result.session_id, tool_response)
            preview_result.status = (
                "executed_successfully"
                if tool_response.status in {"success", "invalid"}
                else "execution_failed"
            )
            preview_result.message = (
                "Tool call executed successfully through the agent shell."
                if preview_result.status == "executed_successfully"
                else f"Tool call finished with status '{tool_response.status}'."
            )
            return preview_result

        if preview_result.execution_plan.requires_confirmation and not force_run:
            preview_result.status = "preview_requires_confirmation"
            preview_result.message = (
                "Plan preview requires confirmation before execution."
            )
            return preview_result

        task_response = run_governance_task(preview_result.task_request)
        if preview_result.session_id:
            set_last_task_context(
                preview_result.session_id,
                task_request=preview_result.task_request,
                task_response=task_response,
            )
            if task_response.exported_files:
                set_last_exported_files(
                    preview_result.session_id,
                    task_response.exported_files,
                )

        status = (
            "executed_successfully"
            if task_response.status == "success"
            else "execution_failed"
        )
        message = (
            "Task executed successfully through the agent shell."
            if task_response.status == "success"
            else f"Task execution finished with status '{task_response.status}'."
        )

        return AgentShellResult(
            interpreted_intent=preview_result.interpreted_intent,
            task_request=preview_result.task_request,
            execution_plan=preview_result.execution_plan,
            resolved_context=preview_result.resolved_context,
            resolution_applied=preview_result.resolution_applied,
            task_response=task_response,
            session_id=preview_result.session_id,
            status=status,
            message=message,
        )

    def run_from_plan(
        self,
        task_request: GovernanceTaskRequest,
        session_id: str | None = None,
    ) -> AgentShellResult:
        """Run directly from a standardized task request and return its derived plan."""
        resolved_session_id = self._ensure_session(session_id)
        interpreted_intent = self._build_direct_intent(task_request)
        resolution_result = self.context_resolver.resolve(
            raw_text=interpreted_intent.raw_text,
            task_request=task_request,
            session_id=resolved_session_id,
        )
        resolved_task_request = resolution_result.resolved_task_request
        execution_plan = self.planner.build_plan(
            interpreted_intent,
            resolved_task_request,
            resolution_result.resolved_context,
        )

        append_request_to_session(resolved_session_id, interpreted_intent.raw_text)
        session = append_plan_to_session(resolved_session_id, execution_plan)
        session.last_task_request = resolved_task_request

        if not execution_plan.validation_passed:
            session.last_task_response = None
            save_session(session)
            return AgentShellResult(
                interpreted_intent=interpreted_intent,
                task_request=resolved_task_request,
                execution_plan=execution_plan,
                resolved_context=resolution_result.resolved_context,
                resolution_applied=resolution_result.resolution_applied,
                task_response=None,
                session_id=resolved_session_id,
                status="validation_failed",
                message="Direct execution was blocked because plan validation failed.",
            )

        task_response = run_governance_task(resolved_task_request)
        session.last_task_response = task_response
        save_session(session)
        if task_response.exported_files:
            set_last_exported_files(resolved_session_id, task_response.exported_files)

        status = (
            "executed_successfully"
            if task_response.status == "success"
            else "execution_failed"
        )
        message = (
            "Direct task request executed successfully through the agent shell."
            if task_response.status == "success"
            else f"Direct task execution finished with status '{task_response.status}'."
        )
        return AgentShellResult(
            interpreted_intent=interpreted_intent,
            task_request=resolved_task_request,
            execution_plan=execution_plan,
            resolved_context=resolution_result.resolved_context,
            resolution_applied=resolution_result.resolution_applied,
            task_response=task_response,
            session_id=resolved_session_id,
            status=status,
            message=message,
        )


# TODO: extend the shell service with multi-turn parameter completion and optional autonomous planning once the current preview-first path is stable.

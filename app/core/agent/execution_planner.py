"""Rule-based execution planner for the lightweight agent shell."""

from app.core.agent.agent_loader import load_agent_shell_config
from app.core.models.execution_plan import ExecutionPlan
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.interpreted_intent import InterpretedIntent
from app.core.models.resolved_context import ResolvedContext
from app.core.orchestrator.profile_exceptions import WorkflowProfileNotFoundError
from app.core.orchestrator.profile_loader import get_workflow_profile

STAGE_LABELS = {
    "diagnosis": "diagnosis",
    "mapping": "mapping",
    "stg": "STG suggestion",
    "quality_rule_recommendation": "quality rule recommendation",
    "review_replay": "review replay",
    "quality_review_replay": "quality rule review replay",
    "execution_package_build": "execution package build",
}


class ExecutionPlanner:
    """Build explainable execution plans from interpreted intent and task requests."""

    @staticmethod
    def infer_stages_from_profile(profile_name: str) -> list[str]:
        """Infer execution stages from a configured workflow profile."""
        profile = get_workflow_profile(profile_name)
        return list(profile.stages)

    @staticmethod
    def infer_output_mode(profile_name: str) -> str | None:
        """Infer suggested output mode from workflow profile metadata."""
        profile = get_workflow_profile(profile_name)
        return profile.default_report_mode

    def infer_confirmation_requirement(self, profile_name: str) -> bool:
        """Determine whether the plan requires explicit confirmation."""
        config = load_agent_shell_config()
        confirmation_policy = config.get("confirmation_policy", {})
        required_profiles = {
            str(item).strip()
            for item in confirmation_policy.get("require_confirmation_for_profiles", [])
        }
        auto_run_profiles = {
            str(item).strip()
            for item in confirmation_policy.get("auto_run_profiles", [])
        }

        if profile_name in required_profiles:
            return True
        if profile_name in auto_run_profiles:
            return False
        return False

    def validate_task_request(self, task_request: GovernanceTaskRequest) -> list[str]:
        """Validate basic execution parameters before the router runs."""
        config = load_agent_shell_config()
        validation_policy = config.get("validation_policy", {})
        messages: list[str] = []

        try:
            get_workflow_profile(task_request.profile_name)
        except WorkflowProfileNotFoundError:
            messages.append(
                f"Workflow profile '{task_request.profile_name}' does not exist."
            )

        if bool(validation_policy.get("require_file_path", True)) and not task_request.file_path:
            messages.append("A local file_path is required before this plan can run.")

        return messages

    @staticmethod
    def build_plan_summary(
        profile_name: str,
        stages: list[str],
        file_path: str | None,
        export_reports: bool,
        apply_review_replay: bool,
        resolved_context: ResolvedContext | None = None,
    ) -> str:
        """Build a readable summary for preview in UI or API."""
        stage_text = " + ".join(STAGE_LABELS.get(stage, stage) for stage in stages) or profile_name
        file_text = (
            "on the provided metadata file"
            if file_path
            else "after a metadata file is provided"
        )
        if resolved_context and "file_path" in resolved_context.autofilled_parameters:
            file_text = "on the session-resolved metadata file"
        summary = f"This plan will run {stage_text} {file_text}."
        if export_reports:
            summary += " Reports will be exported after a successful run."
        if apply_review_replay:
            summary += " Saved review overrides will be replayed."
        if resolved_context:
            if "file_path" in resolved_context.autofilled_parameters:
                summary += " File path was autofilled from the current session."
            if "output_dir" in resolved_context.autofilled_parameters:
                summary += " Output directory was autofilled from the last session export."
            if resolved_context.ambiguity_detected:
                summary += (
                    " Context resolution detected multiple candidates and left "
                    "ambiguous parameters unchanged."
                )
        return summary

    @staticmethod
    def build_context_validation_messages(
        resolved_context: ResolvedContext | None,
    ) -> list[str]:
        """Convert resolved context messages into plan-facing validation notes."""
        if resolved_context is None:
            return []
        return list(resolved_context.messages)

    def build_plan(
        self,
        interpreted_intent: InterpretedIntent,
        task_request: GovernanceTaskRequest,
        resolved_context: ResolvedContext | None = None,
    ) -> ExecutionPlan:
        """Build a validated execution plan from one interpreted intent."""
        try:
            stages = self.infer_stages_from_profile(task_request.profile_name)
            suggested_output_mode = self.infer_output_mode(task_request.profile_name)
        except WorkflowProfileNotFoundError as exc:
            return ExecutionPlan(
                raw_text=interpreted_intent.raw_text,
                profile_name=task_request.profile_name,
                stages=[],
                apply_review_replay=task_request.apply_review_replay,
                export_reports=task_request.export_reports,
                file_path=task_request.file_path,
                requires_confirmation=False,
                validation_passed=False,
                validation_messages=self.build_context_validation_messages(
                    resolved_context
                )
                + [str(exc)],
                autofilled_parameters=(
                    dict(resolved_context.autofilled_parameters)
                    if resolved_context
                    else {}
                ),
                context_messages=(
                    list(resolved_context.messages) if resolved_context else []
                ),
                suggested_output_mode=None,
                summary=(
                    f"Execution planning failed because workflow profile "
                    f"'{task_request.profile_name}' could not be resolved."
                ),
            )

        context_validation_messages = self.build_context_validation_messages(
            resolved_context
        )
        blocking_validation_messages = self.validate_task_request(task_request)
        validation_messages = context_validation_messages + blocking_validation_messages
        validation_passed = not blocking_validation_messages
        requires_confirmation = self.infer_confirmation_requirement(
            task_request.profile_name
        )

        return ExecutionPlan(
            raw_text=interpreted_intent.raw_text,
            profile_name=task_request.profile_name,
            stages=stages,
            apply_review_replay=task_request.apply_review_replay,
            export_reports=task_request.export_reports,
            file_path=task_request.file_path,
            requires_confirmation=requires_confirmation,
            validation_passed=validation_passed,
            validation_messages=validation_messages,
            autofilled_parameters=(
                dict(resolved_context.autofilled_parameters)
                if resolved_context
                else {}
            ),
            context_messages=list(resolved_context.messages) if resolved_context else [],
            suggested_output_mode=suggested_output_mode,
            summary=self.build_plan_summary(
                profile_name=task_request.profile_name,
                stages=stages,
                file_path=task_request.file_path,
                export_reports=task_request.export_reports,
                apply_review_replay=task_request.apply_review_replay,
                resolved_context=resolved_context,
            ),
        )


# TODO: extend the planner with richer branch planning and optional LLM-assisted plan drafting in future versions.

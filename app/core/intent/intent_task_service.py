"""Lightweight service for interpreting and optionally running natural-language tasks."""

from app.core.intent.intent_interpreter import IntentInterpreter
from app.core.models.intent_execution_result import IntentExecutionResult
from app.core.orchestrator.task_service import run_governance_task


def interpret_and_build_request(
    text: str,
    file_path: str | None = None,
) -> IntentExecutionResult:
    """Interpret task text and build a standard governance task request."""
    interpreter = IntentInterpreter()
    interpreted_intent = interpreter.interpret(text=text, file_path=file_path)
    task_request = interpreter.build_task_request(
        interpreted_intent,
        file_path=file_path,
    )
    return IntentExecutionResult(
        interpreted_intent=interpreted_intent,
        task_request=task_request,
        task_response=None,
    )


def interpret_and_run_task(
    text: str,
    file_path: str | None = None,
) -> IntentExecutionResult:
    """Interpret task text, build a task request, and run it through the router."""
    execution_result = interpret_and_build_request(text=text, file_path=file_path)
    if not execution_result.task_request.file_path:
        execution_result.task_response = run_governance_task(
            execution_result.task_request
        )
        if execution_result.interpreted_intent.message:
            execution_result.interpreted_intent.message += (
                " Task execution could not proceed because file_path is missing."
            )
        return execution_result

    execution_result.task_response = run_governance_task(
        execution_result.task_request
    )
    return execution_result


# TODO: extend this service with optional multi-turn completion once intent parsing remains deterministic and reviewable.

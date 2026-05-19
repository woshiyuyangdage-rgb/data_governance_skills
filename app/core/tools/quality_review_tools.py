"""Quality review tool handlers for the governance executor."""

from typing import Protocol

from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.tool_call_response import ToolCallResponse
from app.core.models.workflow_result import WorkflowResult
from app.core.review.quality_batch_review_service import (
    bulk_accept_by_rule_type,
    bulk_accept_by_table,
    bulk_mark_manual_review_by_low_confidence,
    summarize_review_queue,
)
from app.core.review.quality_override_store import save_quality_rule_review_records
from app.core.review.quality_review_service import (
    apply_quality_rule_overrides_to_results,
    build_confirmed_quality_rules,
    build_quality_rule_review_records_from_results,
    summarize_quality_rule_review_records,
)
from app.core.tools.quality_tool_payloads import (
    coerce_cross_field_quality_rules,
    coerce_quality_review_records,
    coerce_quality_rule_suggestions,
    cross_field_rules_as_suggestions,
)


class QualityReviewToolContext(Protocol):
    """Subset of executor helpers used by quality review resolution functions."""

    def _optional_workflow_result(
        self, arguments: dict[str, object]
    ) -> WorkflowResult | None: ...

    def _optional_string(
        self, arguments: dict[str, object], name: str
    ) -> str | None: ...


def _resolve_quality_rule_inputs_from_arguments(
    context: QualityReviewToolContext,
    arguments: dict[str, object],
) -> tuple[list[QualityRuleSuggestion], WorkflowResult | None]:
    """Resolve review inputs from direct payloads or a workflow result."""
    workflow_result = context._optional_workflow_result(arguments)
    suggestions = coerce_quality_rule_suggestions(
        arguments.get("quality_rule_suggestions")
    )
    cross_field_rules = coerce_cross_field_quality_rules(
        arguments.get("cross_field_quality_rules")
    )
    if workflow_result is not None:
        if not suggestions:
            suggestions = list(workflow_result.quality_rule_suggestions)
        if not cross_field_rules:
            cross_field_rules = list(workflow_result.cross_field_quality_rules)
    suggestions = suggestions + cross_field_rules_as_suggestions(cross_field_rules)
    return suggestions, workflow_result


class QualityReviewToolMixin:
    """Tool handlers for quality rule review and batch review flows."""

    def review_quality_rules(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Review quality rule suggestions and build confirmed quality rules."""
        tool_name = "review_quality_rules"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="quality_review",
        )
        try:
            suggestions, _ = _resolve_quality_rule_inputs_from_arguments(
                self,
                arguments,
            )
            if not suggestions:
                raise ValueError(
                    "quality_rule_suggestions, cross_field_quality_rules, or a"
                    " workflow_result with suggestions is required."
                )

            records = coerce_quality_review_records(arguments.get("records"))
            if not records:
                review_inputs = arguments.get("review_inputs")
                if review_inputs is None:
                    review_inputs = {}
                if not isinstance(review_inputs, dict):
                    raise ValueError(
                        "review_inputs must be an object keyed by rule id."
                    )
                records = build_quality_rule_review_records_from_results(
                    suggestions,
                    review_inputs,
                    source=self._optional_string(arguments, "source") or "tool",
                )

            reviewed_suggestions, applied_count, _ = (
                apply_quality_rule_overrides_to_results(
                    suggestions,
                    records,
                )
            )
            confirmed_rules = build_confirmed_quality_rules(suggestions, records)
            summary = summarize_quality_rule_review_records(
                records,
                confirmed_count=len(confirmed_rules),
            )
            saved_payload = None
            if bool(arguments.get("save_overrides", False)):
                saved_payload = save_quality_rule_review_records(records)

            result_payload = {
                "review_records": [record.model_dump() for record in records],
                "reviewed_quality_rule_suggestions": [
                    suggestion.model_dump() for suggestion in reviewed_suggestions
                ],
                "confirmed_quality_rules": [
                    rule.model_dump() for rule in confirmed_rules
                ],
                "quality_rule_review_summary": summary,
                "applied_quality_review_count": applied_count,
                "saved": saved_payload,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Quality rules were reviewed and confirmed results were built.",
                review_summary=summary,
                operation="quality_review",
                confirmed_rule_count=len(confirmed_rules),
                field_rule_count=sum(
                    1 for rule in suggestions if rule.rule_scope == "field"
                ),
                cross_field_rule_count=sum(
                    1 for rule in suggestions if rule.rule_scope == "cross_field"
                ),
                low_confidence_rule_count=sum(
                    1
                    for rule in suggestions
                    if rule.confidence is not None and rule.confidence <= 0.4
                ),
                review_queue_summary=summarize_review_queue(suggestions),
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Quality rules were reviewed and confirmed results were built.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to review quality rules: {exc}",
                operation="quality_review",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to review quality rules.",
                None,
                trace,
            )

    def batch_review_quality_rules(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Build batch quality rule review records from simple local policies."""
        tool_name = "batch_review_quality_rules"
        action = (self._optional_string(arguments, "action") or "").lower()
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="quality_batch_review",
        )
        try:
            suggestions, _ = _resolve_quality_rule_inputs_from_arguments(
                self,
                arguments,
            )
            if not suggestions:
                raise ValueError("No quality rules were provided for batch review.")

            if action == "accept_by_rule_type":
                records = bulk_accept_by_rule_type(
                    suggestions,
                    self._optional_string(arguments, "rule_type") or "",
                    source="tool_batch_review",
                )
            elif action == "accept_by_table":
                records = bulk_accept_by_table(
                    suggestions,
                    self._optional_string(arguments, "table_name") or "",
                    source="tool_batch_review",
                )
            elif action == "mark_low_confidence_manual_review":
                records = bulk_mark_manual_review_by_low_confidence(
                    suggestions,
                    threshold=float(arguments.get("confidence_threshold", 0.4)),
                    source="tool_batch_review",
                )
            else:
                raise ValueError(
                    "action must be accept_by_rule_type, accept_by_table, or"
                    " mark_low_confidence_manual_review."
                )

            summary = summarize_review_queue(suggestions)
            saved_payload = None
            if bool(arguments.get("save_overrides", False)):
                saved_payload = save_quality_rule_review_records(records)
            result_payload = {
                "review_records": [record.model_dump() for record in records],
                "review_queue_summary": summary,
                "saved": saved_payload,
            }
            trace = self._finish_trace(
                trace,
                "success",
                "Batch quality rule review records were built successfully.",
                operation="quality_batch_review",
                field_rule_count=int(summary.get("field_rule_count", 0) or 0),
                cross_field_rule_count=int(
                    summary.get("cross_field_rule_count", 0) or 0
                ),
                low_confidence_rule_count=int(
                    summary.get("low_confidence_rule_count", 0) or 0
                ),
                review_queue_summary=summary,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Batch quality rule review records were built successfully.",
                result_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build batch review records: {exc}",
                operation="quality_batch_review",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build batch review records.",
                None,
                trace,
            )

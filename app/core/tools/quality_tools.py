"""Quality rule and execution package tool handlers for the governance executor."""

from app.core.models.confirmed_quality_rule import ConfirmedQualityRule
from app.core.models.cross_field_quality_rule import CrossFieldQualityRule
from app.core.models.execution_ready_package import ExecutionReadyPackage
from app.core.models.quality_rule_review_record import QualityRuleReviewRecord
from app.core.models.quality_rule_suggestion import QualityRuleSuggestion
from app.core.models.workflow_result import WorkflowResult
from app.core.tools.quality_package_tools import (
    QualityPackageToolMixin,
    _resolve_execution_ready_package_from_arguments,
)
from app.core.tools.quality_recommendation_tools import (
    QualityRecommendationToolMixin,
)
from app.core.tools.quality_review_tools import QualityReviewToolMixin
from app.core.tools.quality_tool_payloads import (
    coerce_confirmed_quality_rules,
    coerce_cross_field_quality_rules,
    coerce_execution_ready_package,
    coerce_quality_review_records,
    coerce_quality_rule_suggestions,
    cross_field_rules_as_suggestions,
)


class QualityToolMixin(
    QualityRecommendationToolMixin,
    QualityReviewToolMixin,
    QualityPackageToolMixin,
):
    """Tool handlers for quality rule review and execution package flows."""

    @staticmethod
    def _coerce_quality_rule_suggestions(
        payload: object,
    ) -> list[QualityRuleSuggestion]:
        return coerce_quality_rule_suggestions(payload)

    @staticmethod
    def _coerce_cross_field_quality_rules(
        payload: object,
    ) -> list[CrossFieldQualityRule]:
        return coerce_cross_field_quality_rules(payload)

    @staticmethod
    def _cross_field_rules_as_suggestions(
        rules: list[CrossFieldQualityRule],
    ) -> list[QualityRuleSuggestion]:
        return cross_field_rules_as_suggestions(rules)

    @staticmethod
    def _coerce_quality_review_records(
        payload: object,
    ) -> list[QualityRuleReviewRecord]:
        return coerce_quality_review_records(payload)

    @staticmethod
    def _coerce_confirmed_quality_rules(
        payload: object,
    ) -> list[ConfirmedQualityRule]:
        return coerce_confirmed_quality_rules(payload)

    @staticmethod
    def _coerce_execution_ready_package(
        payload: object,
    ) -> ExecutionReadyPackage | None:
        return coerce_execution_ready_package(payload)

    def _resolve_execution_ready_package_from_arguments(
        self,
        arguments: dict[str, object],
    ) -> tuple[
        ExecutionReadyPackage,
        WorkflowResult | None,
        list[ConfirmedQualityRule],
    ]:
        return _resolve_execution_ready_package_from_arguments(self, arguments)

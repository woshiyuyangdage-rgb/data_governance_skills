"""Attachment helpers for workflow result enrichment."""

from typing import Any

from pydantic import BaseModel

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.delivery.delivery_service import DeliveryService
from app.core.governance.ai_ready_assessor import AiReadyAssessor
from app.core.governance.backlog_builder import GovernanceBacklogBuilder
from app.core.governance.backlog_sla_calculator import BacklogSlaCalculator
from app.core.governance.gap_classifier import GapClassifier
from app.core.governance.portfolio_aggregator import GovernancePortfolioAggregator
from app.core.governance.progress_snapshot_service import ProgressSnapshotService
from app.core.governance.readiness_assessor import ReadinessAssessor
from app.core.governance.remediation_planner import RemediationPlanner
from app.core.models.workflow_result import WorkflowResult


class WorkflowAttachmentMixin:
    """Attach derived governance artifacts to workflow results."""

    @staticmethod
    def _serialize_model(model: BaseModel) -> dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump()
        return model.dict()

    def _attach_execution_ready_package(
        self,
        result: WorkflowResult,
        profile_name: str,
    ) -> WorkflowResult:
        """Build and attach an execution-ready package to an existing result."""
        builder = ExecutionPackageBuilder()
        package = builder.build_package(
            result.confirmed_quality_rules,
            profile_name=profile_name,
        )
        summary = builder.summarize_package(package)
        skill_outputs = dict(result.skill_outputs)
        skill_outputs["execution_package_output"] = {
            "execution_ready_package": self._serialize_model(package),
            "execution_package_summary": summary,
        }
        result.execution_ready_package = package
        result.execution_package_summary = summary
        result.skill_outputs = skill_outputs
        if result.status == "success":
            result.message = (
                f"{result.message} Execution-ready governance package was also built."
            )
        return result

    def _attach_governance_readiness(
        self,
        result: WorkflowResult,
        package_name: str,
    ) -> WorkflowResult:
        """Attach readiness, gap, and remediation outputs to an existing result."""
        assessor = ReadinessAssessor()
        classifier = GapClassifier()
        planner = RemediationPlanner()
        ai_ready_assessor = AiReadyAssessor()
        readiness_scores = assessor.assess(result)
        governance_gaps = classifier.classify(result)
        remediation_actions = planner.build_actions(readiness_scores, governance_gaps)
        ai_ready_scores = ai_ready_assessor.assess(result)
        ai_ready_summary = ai_ready_assessor.summarize(ai_ready_scores)
        work_package = planner.build_work_package(
            readiness_scores,
            governance_gaps,
            remediation_actions,
            package_name=package_name,
        )
        readiness_summary = planner.summarize(
            readiness_scores,
            governance_gaps,
            remediation_actions,
        )
        skill_outputs = dict(result.skill_outputs)
        skill_outputs["readiness_assessment_output"] = {
            "readiness_scores": [
                self._serialize_model(score) for score in readiness_scores
            ],
            "readiness_summary": readiness_summary,
        }
        skill_outputs["ai_ready_assessment_output"] = {
            "ai_ready_scores": [
                self._serialize_model(score) for score in ai_ready_scores
            ],
            "ai_ready_summary": ai_ready_summary,
        }
        skill_outputs["gap_classification_output"] = {
            "governance_gaps": [
                self._serialize_model(gap) for gap in governance_gaps
            ],
        }
        skill_outputs["remediation_planning_output"] = {
            "remediation_actions": [
                self._serialize_model(action) for action in remediation_actions
            ],
            "governance_work_package": self._serialize_model(work_package),
        }
        result.readiness_scores = readiness_scores
        result.governance_gaps = governance_gaps
        result.remediation_actions = remediation_actions
        result.governance_work_package = work_package
        result.readiness_summary = readiness_summary
        result.ai_ready_scores = ai_ready_scores
        result.ai_ready_summary = ai_ready_summary
        result.skill_outputs = skill_outputs
        if result.status == "success":
            result.message = (
                f"{result.message} Governance readiness and remediation planning were also generated."
            )
        return result

    def _attach_governance_backlog(self, result: WorkflowResult) -> WorkflowResult:
        """Build and attach governance backlog items to an existing result."""
        builder = GovernanceBacklogBuilder()
        backlog_items, backlog_summary = builder.build_backlog(
            result.remediation_actions,
            governance_gaps=result.governance_gaps,
            readiness_scores=result.readiness_scores,
        )
        skill_outputs = dict(result.skill_outputs)
        skill_outputs["backlog_build_output"] = {
            "governance_backlog_items": [
                self._serialize_model(item) for item in backlog_items
            ],
            "backlog_summary": self._serialize_model(backlog_summary),
        }
        result.governance_backlog_items = backlog_items
        result.backlog_summary = backlog_summary
        result.skill_outputs = skill_outputs
        if result.status == "success":
            result.message = f"{result.message} Governance backlog was also built."
        return result

    def _attach_governance_delivery_package(
        self,
        result: WorkflowResult,
        package_name: str,
        output_dir: str | None = None,
    ) -> WorkflowResult:
        """Attach local confirmation workbooks and delivery package outputs."""
        return DeliveryService().build_governance_delivery_package(
            result,
            output_dir=output_dir,
            base_name=package_name,
        )

    def _attach_governance_portfolio(self, result: WorkflowResult) -> WorkflowResult:
        """Attach backlog SLA, portfolio summary, and progress snapshot outputs."""
        sla_statuses = BacklogSlaCalculator().calculate(result.governance_backlog_items)
        portfolio_summary = GovernancePortfolioAggregator().summarize(
            result.governance_backlog_items,
            readiness_scores=result.readiness_scores,
            backlog_sla_statuses=sla_statuses,
        )
        progress_snapshot = ProgressSnapshotService().build_progress_snapshot(
            result.governance_backlog_items,
            backlog_sla_statuses=sla_statuses,
            readiness_scores=result.readiness_scores,
            notes="Generated from workflow portfolio assessment.",
        )
        skill_outputs = dict(result.skill_outputs)
        skill_outputs["backlog_sla_output"] = {
            "backlog_sla_statuses": [
                self._serialize_model(status) for status in sla_statuses
            ],
        }
        skill_outputs["portfolio_aggregation_output"] = {
            "governance_portfolio_summary": self._serialize_model(portfolio_summary),
        }
        skill_outputs["progress_snapshot_output"] = {
            "progress_snapshot": self._serialize_model(progress_snapshot),
        }
        result.backlog_sla_statuses = sla_statuses
        result.governance_portfolio_summary = portfolio_summary
        result.progress_snapshot = progress_snapshot
        result.skill_outputs = skill_outputs
        if result.status == "success":
            result.message = (
                f"{result.message} Governance portfolio summary and progress snapshot were also generated."
            )
        return result

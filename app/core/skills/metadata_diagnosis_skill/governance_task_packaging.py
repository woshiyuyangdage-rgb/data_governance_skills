"""Rule-based v1 skill for governance task packaging."""

from collections import defaultdict

from pydantic import BaseModel, Field

from app.core.models.governance_task import GovernanceTask
from app.core.models.issue import Issue
from app.core.skills.base_skill import BaseSkill

DIAGNOSIS_DEFECT_TYPES = {
    "business_ownership_defect",
    "semantic_description_defect",
    "technical_purity_defect",
    "naming_standard_defect",
}


class GovernanceTaskPackagingInput(BaseModel):
    """Input schema for governance task packaging."""

    issues: list[Issue] = Field(default_factory=list)


class GovernanceTaskPackagingOutput(BaseModel):
    """Output schema for governance task packaging."""

    tasks: list[GovernanceTask] = Field(default_factory=list)
    priority_summary: dict[str, int] = Field(default_factory=dict)
    summary: str = ""


class GovernanceTaskPackagingSkill(BaseSkill):
    """Convert diagnosis or raw issues into governance tasks."""

    skill_name = "governance_task_packaging"
    version = "0.2.0"
    description = "Rule-based v1 task packaging for governance execution."

    @staticmethod
    def infer_priority(issues: list[Issue]) -> str:
        """Infer task priority from the highest severity issue."""
        severities = {issue.severity.lower() for issue in issues}
        if "high" in severities:
            return "priority_governance"
        if "medium" in severities:
            return "key_tracking"
        return "continuous_observation"

    @staticmethod
    def infer_owner_role(defect_types: set[str]) -> str:
        """Infer an owner role from grouped defect types."""
        if "business_ownership_defect" in defect_types:
            return "business_data_steward"
        if "technical_purity_defect" in defect_types:
            return "data_architect"
        if "semantic_description_defect" in defect_types:
            return "metadata_manager"
        return "data_governance_engineer"

    @staticmethod
    def build_action_text(defect_types: set[str]) -> str:
        """Build a concise governance action from defect types."""
        actions: list[str] = []
        if "naming_standard_defect" in defect_types:
            actions.append("Review naming conventions and update table or field metadata.")
        if "semantic_description_defect" in defect_types:
            actions.append("Complete missing business descriptions and improve description quality.")
        if "business_ownership_defect" in defect_types:
            actions.append("Clarify business meaning, Chinese labels, and ownership metadata.")
        if "technical_purity_defect" in defect_types:
            actions.append("Assess whether the table should remain in the business metadata catalog.")
        return " ".join(actions) or "Review grouped metadata governance issues."

    @staticmethod
    def _preferred_issues(issues: list[Issue]) -> list[Issue]:
        diagnosis_issues = [
            issue for issue in issues if issue.issue_type in DIAGNOSIS_DEFECT_TYPES
        ]
        return diagnosis_issues or issues

    @classmethod
    def group_issues_to_tasks(cls, issues: list[Issue]) -> dict[str, list[Issue]]:
        """Group selected issues by object name for task generation."""
        grouped: dict[str, list[Issue]] = defaultdict(list)
        for issue in cls._preferred_issues(issues):
            grouped[issue.object_name].append(issue)
        return dict(grouped)

    def run(
        self, payload: GovernanceTaskPackagingInput
    ) -> GovernanceTaskPackagingOutput:
        """Package diagnosis or raw issues into governance tasks."""
        grouped_issues = self.group_issues_to_tasks(payload.issues)
        tasks: list[GovernanceTask] = []
        priority_summary: dict[str, int] = defaultdict(int)

        for task_index, (object_name, grouped) in enumerate(grouped_issues.items(), start=1):
            defect_types = {issue.issue_type for issue in grouped}
            priority = self.infer_priority(grouped)
            tasks.append(
                GovernanceTask(
                    task_id=f"{self.skill_name}-{task_index}",
                    issue_ids=[issue.issue_id for issue in grouped],
                    priority=priority,
                    action=self.build_action_text(defect_types),
                    suggested_owner_role=self.infer_owner_role(defect_types),
                    acceptance_criteria=(
                        "Required metadata fields are completed and naming issues are resolved."
                    ),
                )
            )
            priority_summary[priority] += 1

        # TODO: add batch-level task templates and ownership escalation rules.
        return GovernanceTaskPackagingOutput(
            tasks=tasks,
            priority_summary=dict(priority_summary),
            summary=(
                f"Packaged {len(payload.issues)} input issues into {len(tasks)} governance tasks."
            ),
        )

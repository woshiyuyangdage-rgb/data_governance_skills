"""Project template service for applying project-oriented defaults."""

from app.core.domain.domain_pack_loader import get_domain_pack
from app.core.domain.domain_pack_matcher import DomainPackMatcher
from app.core.models.governance_task_request import GovernanceTaskRequest
from app.core.models.project_template_run_result import ProjectTemplateRunResult
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.profile_loader import get_workflow_profile
from app.core.orchestrator.task_service import run_governance_task
from app.core.parser.loader import load_metadata_file
from app.core.rules.config_loader import get_domain_delivery_templates_config
from app.core.templates.project_template_loader import get_project_template


class ProjectTemplateService:
    """Apply domain defaults and run existing workflow profiles."""

    @staticmethod
    def _delivery_defaults(domain_pack_name: str | None) -> dict[str, object]:
        if not domain_pack_name:
            return {}
        defaults = get_domain_delivery_templates_config().get("delivery_defaults", {})
        return dict(defaults.get(domain_pack_name, {}))

    def build_project_template_request(
        self,
        template_name: str,
        file_path: str | None = None,
        domain_pack_name: str | None = None,
        output_dir: str | None = None,
    ) -> GovernanceTaskRequest:
        """Build a workflow request from a project template."""
        template = get_project_template(template_name)
        profile = get_workflow_profile(template.base_workflow_profile)
        return GovernanceTaskRequest(
            file_path=file_path,
            profile_name=template.base_workflow_profile,
            apply_review_replay=template.default_review_mode and profile.supports_review_replay,
            export_reports=True,
            preferred_result_mode=None,
            output_dir=output_dir,
            base_filename=template_name,
            domain_pack_name=domain_pack_name or template.default_domain_pack,
            template_name=template_name,
        )

    def apply_project_template_defaults(
        self,
        template_name: str,
        domain_pack_name: str | None = None,
    ) -> dict[str, object]:
        """Return template defaults plus selected domain pack hints."""
        template = get_project_template(template_name)
        selected_domain_pack = domain_pack_name or template.default_domain_pack
        payload: dict[str, object] = {
            "default_outputs": list(template.default_outputs),
            "default_review_mode": template.default_review_mode,
            "base_workflow_profile": template.base_workflow_profile,
            "domain_delivery_defaults": self._delivery_defaults(selected_domain_pack),
        }
        if selected_domain_pack:
            pack = get_domain_pack(selected_domain_pack)
            payload["domain_pack_hints"] = {
                "preferred_group_by": pack.preferred_group_by,
                "default_owner_roles": pack.default_owner_roles,
                "mapping_hints": pack.mapping_hints,
                "quality_rule_hints": pack.quality_rule_hints,
                "cross_field_hints": pack.cross_field_hints,
                "remediation_hints": pack.remediation_hints,
            }
        return payload

    def run_project_template(
        self,
        template_name: str,
        file_path: str,
        domain_pack_name: str | None = None,
        output_dir: str | None = None,
    ) -> WorkflowResult:
        """Run a project template through the existing governance router."""
        template = get_project_template(template_name)
        selected_domain_pack = domain_pack_name or template.default_domain_pack
        domain_match = None
        if selected_domain_pack is None and file_path:
            tables = load_metadata_file(file_path)
            domain_match = DomainPackMatcher().match_domain_pack_from_tables(tables)
            selected_domain_pack = domain_match.matched_pack_name

        request = self.build_project_template_request(
            template_name,
            file_path=file_path,
            domain_pack_name=selected_domain_pack,
            output_dir=output_dir,
        )
        response = run_governance_task(request)
        result = response.result if isinstance(response.result, WorkflowResult) else WorkflowResult.model_validate(response.result)
        result.domain_pack_match = domain_match
        applied_defaults = self.apply_project_template_defaults(
            template_name,
            selected_domain_pack,
        )
        result.project_template_result = ProjectTemplateRunResult(
            template_name=template_name,
            selected_domain_pack=selected_domain_pack,
            applied_defaults=applied_defaults,
            workflow_profile=template.base_workflow_profile,
            status=response.status,
            message=f"Project template '{template_name}' applied.",
        )
        skill_outputs = dict(result.skill_outputs)
        skill_outputs["project_template_output"] = result.project_template_result.model_dump()
        result.skill_outputs = skill_outputs
        return result


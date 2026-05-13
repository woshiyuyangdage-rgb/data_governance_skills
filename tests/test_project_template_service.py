"""Smoke tests for project template service."""

from pathlib import Path

from app.core.templates.project_template_service import ProjectTemplateService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_METADATA_PATH = PROJECT_ROOT / "app" / "data" / "samples" / "sample_metadata.csv"


def test_project_template_request_builds_defaults() -> None:
    service = ProjectTemplateService()
    request = service.build_project_template_request(
        "standard_mapping_confirmation_project",
        file_path=str(SAMPLE_METADATA_PATH),
        domain_pack_name="customer_domain_pack",
    )
    assert request.profile_name == "diagnosis_plus_mapping"
    assert request.template_name == "standard_mapping_confirmation_project"
    assert request.domain_pack_name == "customer_domain_pack"


def test_project_template_defaults_include_domain_hints() -> None:
    defaults = ProjectTemplateService().apply_project_template_defaults(
        "standard_mapping_confirmation_project",
        "customer_domain_pack",
    )
    assert defaults["base_workflow_profile"] == "diagnosis_plus_mapping"
    assert "mapping_confirmation_workbook" in defaults["default_outputs"]
    assert "domain_pack_hints" in defaults


def test_project_template_run_attaches_template_result() -> None:
    result = ProjectTemplateService().run_project_template(
        "standard_mapping_confirmation_project",
        str(SAMPLE_METADATA_PATH),
        domain_pack_name="customer_domain_pack",
    )
    assert result.status == "success"
    assert result.project_template_result is not None
    assert result.project_template_result.workflow_profile == "diagnosis_plus_mapping"


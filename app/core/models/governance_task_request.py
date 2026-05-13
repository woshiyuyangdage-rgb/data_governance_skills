"""Unified governance task request model."""

from pydantic import BaseModel


class GovernanceTaskRequest(BaseModel):
    """Structured task request for the governance router."""

    file_path: str | None = None
    file_paths: list[str] | None = None
    profile_name: str
    workbook_type: str | None = None
    domain_pack_name: str | None = None
    template_name: str | None = None
    intake_profile_name: str | None = None
    auto_match_template: bool = False
    sheet_name: str | None = None
    confirmation_template_name: str | None = None
    apply_review_replay: bool = False
    export_reports: bool = False
    preferred_result_mode: str | None = None
    output_dir: str | None = None
    base_filename: str | None = None

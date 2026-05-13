"""Input model for the quality-rule recommendation tool."""

from pydantic import BaseModel


class QualityRuleToolRequest(BaseModel):
    """Tool request for running quality rule recommendation workflows."""

    file_path: str | None = None
    profile_name: str | None = None
    apply_review_replay: bool = False
    export_reports: bool = False
    preferred_result_mode: str | None = None
    output_dir: str | None = None
    base_filename: str | None = None

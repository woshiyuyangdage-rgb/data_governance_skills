"""Compatibility exports for template and intake job routes.

New code should import from `app.api.routes_jobs_intake`.
"""

from app.api.routes_jobs_intake import (
    diagnose_confirmation_template,
    diagnose_metadata_intake_template,
    get_domain_governance_packs,
    get_project_templates,
    import_confirmation_template_and_rerun,
    import_confirmation_with_template,
    match_domain_governance_pack,
    normalize_metadata_input,
    router,
    run_governance_with_intake_profile,
    run_project_template,
)

__all__ = [
    "diagnose_confirmation_template",
    "diagnose_metadata_intake_template",
    "get_domain_governance_packs",
    "get_project_templates",
    "import_confirmation_template_and_rerun",
    "import_confirmation_with_template",
    "match_domain_governance_pack",
    "normalize_metadata_input",
    "router",
    "run_governance_with_intake_profile",
    "run_project_template",
]

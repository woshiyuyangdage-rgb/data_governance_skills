"""Readiness and delivery entries for the jobs catalog."""

DELIVERY_JOB_ITEMS = [
    {
        "name": "assess_governance_readiness",
        "method": "POST",
        "path": "/jobs/assess-governance-readiness",
        "description": "Assess governance readiness scores and classify governance gaps.",
    },
    {
        "name": "build_governance_work_package",
        "method": "POST",
        "path": "/jobs/build-governance-work-package",
        "description": "Build remediation actions and an exportable governance work package.",
    },
    {
        "name": "governance_readiness_summary",
        "method": "GET",
        "path": "/jobs/governance-readiness-summary",
        "description": "Return a lightweight summary placeholder for readiness/remediation capability.",
    },
]

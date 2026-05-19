"""Backlog, portfolio, and progress entries for the jobs catalog."""

BACKLOG_JOB_ITEMS = [
    {
        "name": "build_governance_backlog",
        "method": "POST",
        "path": "/jobs/build-governance-backlog",
        "description": "Build local governance backlog items from remediation actions.",
    },
    {
        "name": "governance_backlog",
        "method": "GET",
        "path": "/jobs/governance-backlog",
        "description": "List persisted governance backlog items with optional filters.",
    },
    {
        "name": "update_governance_backlog_status",
        "method": "POST",
        "path": "/jobs/governance-backlog/{backlog_id}/status",
        "description": "Update one persisted governance backlog item status.",
    },
    {
        "name": "governance_backlog_summary",
        "method": "GET",
        "path": "/jobs/governance-backlog-summary",
        "description": "Return persisted governance backlog summary counts.",
    },
    {
        "name": "assess_governance_portfolio",
        "method": "POST",
        "path": "/jobs/assess-governance-portfolio",
        "description": "Assess backlog SLA, portfolio summary, and progress snapshot outputs.",
    },
    {
        "name": "generate_progress_snapshot",
        "method": "POST",
        "path": "/jobs/generate-progress-snapshot",
        "description": "Generate and optionally save a local governance progress snapshot.",
    },
    {
        "name": "governance_progress_snapshots",
        "method": "GET",
        "path": "/jobs/governance-progress-snapshots",
        "description": "List saved local governance progress snapshots.",
    },
    {
        "name": "governance_portfolio_summary",
        "method": "GET",
        "path": "/jobs/governance-portfolio-summary",
        "description": "Return current persisted backlog portfolio summary.",
    },
]

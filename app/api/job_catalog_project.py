"""Project workspace entries for the jobs catalog."""

PROJECT_WORKSPACE_JOB_ITEMS = [
    {
        "name": "project_workspaces",
        "method": "GET",
        "path": "/jobs/project-workspaces",
        "description": "List local governance project workspaces.",
    },
    {
        "name": "create_project_workspace",
        "method": "POST",
        "path": "/jobs/project-workspaces",
        "description": "Create a local governance project workspace.",
    },
    {
        "name": "project_workspace_detail",
        "method": "GET",
        "path": "/jobs/project-workspaces/{workspace_id}",
        "description": "Load a local governance project workspace.",
    },
    {
        "name": "record_project_workspace_run",
        "method": "POST",
        "path": "/jobs/project-workspaces/{workspace_id}/runs",
        "description": "Record one workflow run in a project workspace.",
    },
    {
        "name": "set_project_workspace_review_state",
        "method": "POST",
        "path": "/jobs/project-workspaces/{workspace_id}/review-state",
        "description": "Set review queue counts for a project workspace.",
    },
    {
        "name": "attach_project_workspace_artifact",
        "method": "POST",
        "path": "/jobs/project-workspaces/{workspace_id}/artifacts",
        "description": "Attach a local artifact to a project workspace.",
    },
]

# Project Workspace Spec

Project workspaces group a local governance initiative across workflow runs, review queues, and exported artifacts.

## Purpose

A workspace answers four operational questions:

- Which governance initiative is this work part of?
- Which workflow runs have been executed for it?
- Which review queues still need attention?
- Which reports, workbooks, packages, or manifests were delivered?

The feature is local-first. It stores JSON files under `app/data/project_workspaces/` and does not create external tickets or connect to a database.

## Data Model

- `ProjectWorkspace`: project-level metadata, status, runs, review states, artifacts, tags, and notes.
- `ProjectWorkspaceRun`: one workflow execution record, including profile, status, input file, summary, and linked artifact ids.
- `ProjectWorkspaceReviewState`: review queue counts for mapping, STG, quality rules, backlog, delivery confirmation, or any named queue.
- `ProjectWorkspaceArtifact`: local output path for a report, workbook, execution package, delivery bundle, manifest, or evidence file.
- `ProjectWorkspaceSummary`: compact index entry for listing workspaces.

## Storage

- Workspace JSON files are stored in `app/data/project_workspaces/`.
- `workspace_index.json` stores compact listing summaries and can be rebuilt from workspace files.
- `_snapshots/` stores the previous workspace JSON when an existing workspace is saved.
- Runtime workspace data is ignored by git; only placeholder files are kept in the repository.

The storage layer is intentionally file based so tests, demos, and local governance workshops can run without external services.

## API

- `GET /jobs/project-workspaces`
- `POST /jobs/project-workspaces`
- `GET /jobs/project-workspaces/{workspace_id}`
- `POST /jobs/project-workspaces/{workspace_id}/runs`
- `POST /jobs/project-workspaces/{workspace_id}/review-state`
- `POST /jobs/project-workspaces/{workspace_id}/artifacts`

Route responses include a workspace summary where relevant. The summary exposes latest run status, run count, unresolved review count, artifact count, owner, tags, and timestamps.

## UI

The Streamlit workbench exposes the feature through `app/ui/pages/20_project_workspace.py` in the governance management section.

The page supports:

- creating a project workspace with owner, domain pack, template, tags, and notes;
- selecting an existing workspace and rebuilding the local index;
- syncing the current workflow result into a workspace in one action;
- recording the current workflow result as a workspace run;
- updating review queue counts;
- attaching local reports, workbooks, packages, manifests, or evidence files;
- viewing run timelines and comparing two runs;
- viewing workspace runs, review queues, artifacts, and raw JSON.

## Workflow Result Sync

`app/core/governance/project_workspace_sync_service.py` converts a `WorkflowResult` into project workspace records.

The sync service:

- records one project run with a compact workflow summary;
- syncs manual review, quality-rule review, and backlog summaries into review queues;
- attaches rule exports, execution package exports, confirmation workbooks, delivery package directories, and generated delivery files;
- skips artifact paths already registered in the workspace.

## Run Insights

`app/core/governance/project_workspace_insights_service.py` builds lightweight project run analytics from saved workspace runs.

The insights service:

- builds a run timeline from each run's compact `result_summary`;
- normalizes legacy and current metric names such as `diagnosis_issues` and `issue_count`;
- compares two runs and reports baseline value, target value, delta, and direction;
- treats lower issue and backlog counts as improvements, and higher coverage/output counts as improvements.

## Example Flow

1. Create a workspace for a data-domain cleanup initiative.
2. Record each workflow run against the workspace.
3. Attach generated reports, confirmation workbooks, and delivery packages.
4. Update review queue counts after human confirmation.
5. Use the workspace summary to track unresolved review load and latest run status.

## Non Goals

- It does not execute data quality checks in a production database.
- It does not create external tickets or write to enterprise workflow systems.
- It does not replace the existing delivery package or backlog models; it links their outputs to a project-level workspace.

## Next Extensions

- Add optional charts for run trends in the Streamlit workspace page.

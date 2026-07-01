# Platform Metrics Spec

The platform metrics dashboard summarizes local data produced by the governance workbench.

## Purpose

The dashboard answers five operational questions:

- How many project workspaces, runs, review items, and artifacts exist locally?
- Which governance workflows are being used most often?
- Which workspaces carry the most review load?
- What is the current backlog distribution by status, priority, and owner?
- How much local output and audit data has the platform produced?

## Data Sources

- Project workspaces under `app/data/project_workspaces/`
- Persisted backlog items under `app/data/governance_backlog/`
- Local execution traces under `app/data/audit/execution_traces/`
- Local output files under `outputs/`

The service is local-first and read-only. It does not call external systems and does not mutate runtime data.

## Core Service

`app/core/governance/platform_metrics_service.py` aggregates local stores into a `PlatformMetrics` model.

The service provides:

- top-level KPI values;
- workspace ranking rows;
- workspace, run, workflow, artifact, backlog, and trace distributions;
- output directory file inventory;
- recent activity rows across workspaces, backlog items, and traces.
- health signals for failed traces, blocked backlog, high review load, missing artifacts, and large output directories.
- workspace delivery completeness scoring.

Bad JSON files, missing directories, and inaccessible files are skipped so the dashboard remains available during local development.

Optional filters can limit the aggregation by workspace status, backlog status, trace status, and recent activity count.

## UI

The Streamlit workbench exposes the dashboard through `app/ui/pages/21_platform_metrics.py` in the governance management section.

The page contains:

- KPI row;
- overview distributions;
- workspace ranking;
- health signal cards and details;
- backlog status, priority, and owner distributions;
- trace status and tool distributions;
- output file inventory;
- raw JSON for audit and debugging.

The page also provides:

- filters for workspace, backlog, and trace status;
- configurable recent activity count;
- minimum delivery completeness filter;
- JSON export for the full metrics payload;
- CSV exports for workspace metrics and recent activity rows;
- human-readable output size display.

## Health Signals

The dashboard derives health signals from the same local metrics payload.

Current signals include:

- `trace_failure`: failed or error traces exist in the scanned trace window;
- `blocked_backlog`: blocked backlog items exist;
- `pending_review_load`: project workspace review load exceeds the warning threshold;
- `run_without_artifacts`: workspaces have recorded runs but no linked artifacts;
- `low_delivery_completeness`: workspaces with runs are below the delivery completeness threshold;
- `large_output_file_count`: output file count exceeds the warning threshold;
- `large_output_size`: output bytes exceed the warning threshold;
- `platform_health`: fallback OK signal when no risks are detected.

Signals are advisory and local-only. They do not block workflow execution.

## Delivery Completeness

Each workspace receives a delivery completeness score from 0 to 100.

The current score checks six components:

- at least one run record;
- at least one review state;
- at least one linked artifact;
- a confirmation workbook artifact;
- an execution package artifact;
- a delivery package, delivery artifact, or manifest artifact.

Levels are:

- `complete`: 85 or above;
- `mostly_complete`: 60 to 84;
- `partial`: 1 to 59;
- `not_started`: 0.

## Non Goals

- It does not replace project workspace run insights.
- It does not persist derived analytics snapshots.
- It does not connect to production databases, ticket systems, or cloud observability systems.

## Next Extensions

- Add historical snapshots for platform-level trends.
- Add filters by time range and workspace owner.
- Add export buttons for platform metrics JSON and Excel.

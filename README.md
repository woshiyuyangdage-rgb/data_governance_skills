# Data Governance Skills

`data_governance_skills` is a local single-user MVP for rule-based metadata governance. It keeps the core P0 diagnosis path stable while adding standard mapping, STG structure suggestions, quality rule recommendation, human review replay, execution-ready packages, readiness assessment, backlog/portfolio summaries, local delivery assets, a Streamlit workbench, FastAPI routes, and a local tool/adapter surface.

The project is intentionally local and rule-based. It creates decision-support and export assets; it does not execute database quality checks, call LLMs, create tickets, or integrate with external workflow systems.

## Quick Start

Use Python 3.10 or newer.

```bash
python --version
python -m pip install -r requirements.txt
```

Install local development tools:

```bash
python -m pip install -r requirements-dev.txt
```

Run the FastAPI app:

```bash
python -m uvicorn app.main:app --reload
```

Run the Streamlit workbench:

```bash
python -m streamlit run app/ui/streamlit_app.py
```

Run checks:

```bash
python -m pytest -q
python -m app.maintenance doctor
python -m app.maintenance quick-check
python -m ruff check app tests
```

Clean local cache artifacts:

```bash
python -m app.maintenance clean-local-artifacts
```

## Core Flow

The normal local workflow is:

`upload metadata -> parse -> diagnose -> map standards -> suggest STG -> recommend quality rules -> review -> replay overrides -> build confirmed rules -> build execution package -> assess readiness -> plan remediation -> build backlog -> assess portfolio -> export reports/assets`

Common workflow profiles include:

- `metadata_diagnosis_only`
- `diagnosis_plus_mapping`
- `diagnosis_mapping_stg`
- `diagnosis_mapping_stg_with_review`
- `diagnosis_mapping_stg_quality`
- `diagnosis_mapping_stg_quality_with_review`
- `diagnosis_mapping_stg_quality_package_with_review`
- `governance_readiness_assessment_with_review`
- `full_governance_work_package`
- `governance_backlog_build`
- `full_governance_backlog_package`
- `governance_portfolio_assessment`
- `full_governance_portfolio_package`
- `mapping_only`
- `stg_only_from_mapping`
- `quality_only_from_stg`
- `quality_only_from_stg_with_review`

Use `python -m app.maintenance commands` to list the most common local commands.

## Input Template

Supported input files are `.csv` and `.xlsx`.

Required and recommended columns:

- `table_name` is required.
- `field_name` is recommended for field-level input.
- Optional columns include `table_name_cn`, `table_description`, `schema_name`, `system_name`, `field_name_cn`, `field_description`, `data_type`, and `nullable`.

Reference files:

- `docs/input_template_spec.md`
- `app/data/samples/sample_metadata.csv`

## Interfaces

Main local interfaces:

- Streamlit workbench: `app/ui/streamlit_app.py`
- FastAPI app: `app/main.py`
- Job routes: `app/api/routes_jobs.py`
- Reports routes: `app/api/routes_reports.py`
- Skill routes: `app/api/routes_skills.py`
- Maintenance CLI: `app/maintenance.py`

Useful FastAPI endpoints:

- `GET /health`
- `GET /jobs/`
- `POST /jobs/run-governance-task`
- `POST /jobs/interpret-governance-task`
- `POST /jobs/agent-shell/plan`
- `POST /jobs/call-tool`
- `GET /jobs/capability-manifest`
- `GET /jobs/config-assets`
- `POST /jobs/review-quality-rules`
- `POST /jobs/build-execution-ready-package`
- `POST /jobs/assess-governance-readiness`
- `POST /jobs/build-governance-backlog`
- `POST /jobs/assess-governance-portfolio`

Example request body for file-based routes:

```json
{
  "file_path": "D:/Projects/data_governance_skills/app/data/samples/sample_metadata.csv"
}
```

## Project Layout

```text
app/
  api/        FastAPI route modules and request models
  config/     YAML configuration assets
  core/       parsers, workflow, skills, governance logic, adapters, reports, models
  data/       sample inputs, dictionaries, standards, local overrides, audit state
  ui/         Streamlit workbench
docs/         specifications and design notes
outputs/      local runtime exports
tests/        pytest coverage for local MVP flows
```

## Documentation Index

Core specs:

- `docs/input_template_spec.md`
- `docs/knowledge_pack_spec.md`
- `docs/workflow_profile_spec.md`
- `docs/intent_interpreter_spec.md`
- `docs/context_resolver_spec.md`
- `docs/agent_shell_spec.md`
- `docs/tool_contract_spec.md`
- `docs/control_plane_spec.md`
- `docs/adapter_layer_spec.md`

Governance capability specs:

- `docs/stg_structure_spec.md`
- `docs/quality_rule_recommendation_spec.md`
- `docs/domain_aware_quality_spec.md`
- `docs/quality_rule_review_and_export_spec.md`
- `docs/execution_ready_package_spec.md`
- `docs/governance_readiness_and_remediation_spec.md`
- `docs/governance_backlog_tracking_spec.md`
- `docs/governance_portfolio_and_progress_spec.md`
- `docs/governance_delivery_package_spec.md`
- `docs/batch_processing_and_incremental_rerun_spec.md`
- `docs/workbook_import_and_roundtrip_spec.md`

Maintenance:

- `docs/maintenance_commands.md`

## Current Boundaries

This project currently does not provide:

- LLM reasoning, embeddings, vector search, or semantic retrieval.
- Database execution, schedulers, queues, Docker, or CI wiring.
- Runtime execution for dbt, Great Expectations, Soda, or custom SQL engines.
- Multi-user approval workflow, permissions, or database-backed state.
- External Jira, Feishu, DingTalk, TAPD, email, SharePoint, or BI integration.
- Automatic owner assignment, reminder delivery, or ticket creation.

The exported artifacts are local JSON, Markdown, Excel, and YAML files intended for review, handoff, and later adapter integration.

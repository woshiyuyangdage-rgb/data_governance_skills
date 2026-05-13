# Data Governance Skills

`data_governance_skills` is a local single-user MVP for rule-based metadata governance. It keeps the existing P0 pipeline stable and extends it with governance knowledge packs, domain governance packs, project template profiles, enterprise metadata intake adapters, a P1 standard mapping skill, a P1.5 STG structure suggestion skill, a P2 quality rule recommendation skill, domain-aware and cross-field quality intelligence, a human-in-the-loop review layer with local override memory, confirmed quality rules, an execution-ready governance package layer, governance readiness scoring, gap classification, remediation planning, governance backlog tracking, governance portfolio summary, SLA-ready backlog metadata, progress snapshots, governance delivery packages and confirmation workbooks, workbook import and confirmation round-trip, multi-file batch processing, fingerprint-based incremental rerun, a workflow-profile-based governance task router, a lightweight natural-language intent interpreter, a session-aware context resolver, an agent shell for preview-first execution, a standard tool contract layer with local execution traces, a lightweight governance control plane for managed configuration assets, and an adapter-ready export layer for future external integration.

The main closed loop is:

`upload one or more metadata files -> parse -> batch grouping -> fingerprint diff -> select rerun scope -> run governance task -> inspect issues/tasks/mapping/stg/quality intelligence -> export confirmation workbook -> external confirmation -> import workbook -> merge updates -> rerun changed objects -> build confirmed quality rules -> build execution-ready package -> assess readiness -> classify gaps -> plan remediation -> build and track governance backlog -> build governance delivery package -> export reports and rule/package/work-package/backlog/portfolio/delivery assets`

## Current Deliverables

The current MVP supports:

- file parsing for `.csv` and `.xlsx`
- rule-based P0 metadata diagnosis
- knowledge-pack-driven naming enhancement
- P1 rule-based standard field mapping recommendation
- P1.5 rule-based STG structure suggestion
- P2 rule-based quality rule recommendation
- domain-aware and cross-field quality rule recommendation
- confidence scoring and review priority hints for quality rules
- batch quality rule review helpers for common local actions
- accept / reject / edit / mark_for_manual_review review actions
- local override persistence and rerun with review memory
- confirmed quality rule construction after review replay
- execution-ready governance package construction from confirmed quality rules
- governance readiness scoring across metadata, mapping, STG, quality rules, and review completion
- governance gap classification and remediation action planning
- exportable governance work package construction
- governance backlog item generation, local status tracking, filtering, summary, and export
- backlog SLA due-date, aging, overdue analysis, governance portfolio summary, owner workload, and local progress snapshots
- governance delivery package and confirmation workbook export for mapping, STG, quality rules, and backlog confirmation
- confirmation workbook import and round-trip merge into review overrides and backlog updates
- multi-file batch processing grouped by `system_name`, `schema_name`, or lightweight `domain_hint`
- fingerprint-based incremental diff with new / changed / unchanged / removed / pending review summaries
- prebuilt domain governance packs for customer, transaction, reference code, and supply chain finance scenarios
- project template profiles that apply default workflow, outputs, review mode, and domain hints in one request
- enterprise metadata intake adapters for standard templates, governance platform exports, and manual inventory worksheets
- rule export adapter for custom JSON packages and first-version dbt tests YAML
- workflow profiles and unified governance task routing
- lightweight natural-language intent interpretation
- session-scoped context resolution and parameter autofill
- agent shell plan preview, validation, context-aware autofill, and confirmation-aware execution
- standard tool contract layer for local callable governance tools
- local execution trace and audit record storage
- governance control plane for managed YAML / JSON / CSV assets
- adapter layer for capability manifest, schema export, and local invocation adaptation
- governance task packaging
- local report export in JSON / Markdown / Excel
- FastAPI demo and file-based execution entrypoints
- Streamlit workbench for Upload -> Metadata Intake -> Intent Runner / Agent Shell / Diagnose -> Review -> Quality Rules -> Execution Package -> Governance Readiness -> Governance Backlog -> Governance Portfolio -> Governance Delivery -> Batch & Incremental Rerun -> Confirmation Import -> Domain & Templates -> Reports -> Tool Console -> Control Plane -> Adapter Console

## Input Template

Supported input granularity:

1. `table-level only`
2. `table + field-level`

The first version mainly targets `table + field-level`.

Standard columns:

- `table_name`
- `table_name_cn`
- `table_description`
- `schema_name`
- `system_name`
- `field_name`
- `field_name_cn`
- `field_description`
- `data_type`
- `nullable`

Column rules:

- `table_name` is required for all files
- `field_name` is recommended for field-level input and may be left blank for table-only rows
- all other columns are optional
- each row represents one field, and table-level information repeats across rows

Reference files:

- template spec: `docs/input_template_spec.md`
- sample file: `app/data/samples/sample_metadata.csv`

## Knowledge Packs

The first governance knowledge packs live under `app/data/`:

- `app/data/dictionaries/abbreviation_dict.csv`
  - expands naming abbreviations such as `cust`, `amt`, `dt`
- `app/data/dictionaries/root_word_dict.csv`
  - normalizes core naming tokens such as `customer`, `transaction`, `audit`

## Domain Governance Packs

Domain governance packs live in `app/config/domain_governance_packs.yaml`. They provide rule-based defaults and hints for common governance scenes:

- `customer_domain_pack`
- `transaction_domain_pack`
- `reference_code_domain_pack`
- `supply_chain_finance_domain_pack`

Each pack can define trigger tokens, preferred grouping, default owner roles, mapping hints, quality rule template hints, cross-field pattern hints, and remediation hints. These values are used as hints and do not override the existing diagnosis, mapping, STG, quality, remediation, or delivery rules.

Domain-aware delivery defaults live in `app/config/domain_delivery_templates.yaml`. They map a selected domain pack to preferred delivery outputs such as mapping confirmation workbooks, STG confirmation workbooks, quality rule confirmation workbooks, backlog workbooks, execution-ready packages, and governance delivery packages.

## Project Template Profiles

Project templates live in `app/config/project_template_profiles.yaml`. A template applies a base workflow profile plus default outputs, review mode, and an optional default domain pack in one request.

Current templates:

- `metadata_inventory_project`
- `standard_mapping_confirmation_project`
- `stg_structure_design_project`
- `quality_rule_build_project`
- `full_governance_delivery_project`

Suggested usage:

- use `customer_domain_pack` with `standard_mapping_confirmation_project` for customer-domain standard mapping confirmation
- use `transaction_domain_pack` with `stg_structure_design_project` for transaction STG structure design
- use `supply_chain_finance_domain_pack` with `full_governance_delivery_project` for full governance delivery

Current boundary: this is a local, rule-based domain pack and template system. It does not perform automatic learning, complex domain inference, ontology management, LLM calls, embeddings, vector search, database persistence, or external project management integration.

Future extensions can add enterprise custom domain packs, domain pack marketplace patterns, project template versioning, and enterprise-specific template adapters.

## Enterprise Metadata Intake Adapters

Enterprise metadata intake adapters let the system accept structured Excel/CSV files that do not already use the standard input column names. The intake layer diagnoses the template, maps source columns to normalized target fields, cleans common values, and produces records compatible with the existing parser and workflow engine.

Current intake profiles live in `app/config/intake_template_profiles.yaml`:

- `standard_metadata_template`
- `governance_platform_export_template`
- `manual_inventory_template`
- `mapping_confirmation_template`
- `quality_rule_confirmation_template`

Field mappings live in `app/config/intake_field_mapping_specs.yaml`, and matching/validation behavior lives in `app/config/intake_diagnosis_policies.yaml`.

## Intake Template Diagnosis

The intake matcher reads CSV headers or Excel sheet headers and compares them with configured field mapping specs. Diagnosis returns the matched profile, confidence, matched sheet, matched headers, missing required target fields, and warnings. Normalization then reports mapped fields, unmapped source columns, row count, table count, and the normalized records.

Suggested usage:

- use `governance_platform_export_template` for governance platform export files
- use `manual_inventory_template` for manual inventory worksheets
- enable auto-match to diagnose a metadata file first, then run a governance workflow with the normalized input

Current boundary: this is rule-based header matching and column mapping for structured Excel/CSV files. It does not perform complex semantic template recognition, OCR, document understanding, LLM calls, embeddings, vector search, or external platform API integration.

Future extensions can add enterprise-specific intake adapters, folder-based intake profiles, semantic header matching, and batch template auto-diagnosis.
- `app/data/standards/standard_fields.csv`
  - provides the local standard field library for mapping recommendations

Reference document:

- `docs/knowledge_pack_spec.md`

Usage note:

- knowledge-pack quality directly affects naming suggestions and mapping accuracy
- when results are weak, improve the dictionaries and standard library before adding more complex logic

## Standard Mapping Skill

The project includes `standard_mapping_recommendation`, a P1 rule-based skill that:

- evaluates field-level metadata against the local standard field library
- ranks candidates using transparent rule scores
- returns `match_score`, `match_reason`, and candidate counts
- flags unmapped or low-confidence fields with explainable issues

This skill does not replace the P0 pipeline. Instead, it is available as an optional extension:

- `run_p0_pipeline`
- `run_p0_plus_mapping`

## STG Structure Suggestion Skill

The project includes `stg_structure_suggestion`, a P1.5 rule-based skill that:

- generates one STG table suggestion per source table
- prefers mapped standard fields when confidence is sufficient
- uses naming enhancement as the next fallback
- falls back to normalized source fields when no stronger signal exists
- normalizes basic data types such as `varchar -> string` and `datetime -> timestamp`
- recommends STG table names such as `ods_customer_snapshot -> stg_customer_snapshot`

This capability produces structure suggestions only. It does not generate executable DDL or SQL.

## Quality Rule Recommendation

The project includes `quality_rule_recommendation`, a P2 rule-based skill that:

- derives field-level quality rule suggestions from confirmed mapping, standard mapping, STG suggestions, and source metadata
- recommends rule types such as `not_null`, `uniqueness`, `value_set`, `numeric_range`, `date_format`, `length_range`, and `regex_format`
- returns explainable `recommendation_source`, `match_basis`, and `reason`
- packages rule suggestions into report-friendly table groups

This skill recommends rules only. Review replay and asset export happen in separate services so suggestions remain reproducible.

## Domain-Aware and Cross-Field Quality Intelligence

Quality recommendation now also emits single-table cross-field and domain-aware rule candidates from metadata and local templates.

Current supported patterns include:

- temporal order hints such as `created_date <= updated_date` and `start_date <= end_date`
- paired presence hints such as `amount -> currency` and `status_code -> status_name`
- reference consistency hints such as `*_id` / `*_name`
- domain templates for customer, transaction/order, and status-like tables

These rules are still assets, not executed checks. They are carried through the same review, confirmed rule, package, report, and export paths as field-level rules.

Reference document:

- `docs/domain_aware_quality_spec.md`

## Review Priority and Confidence

Quality rules now include confidence and `review_priority` metadata:

- stronger template or governance-context matches receive higher confidence
- source fallback and weak reference hints receive lower confidence
- cross-field and low-confidence rules are promoted in the review queue
- batch review helpers can accept high-confidence rule groups or mark low-confidence rules for manual review

## Confirmed Quality Rules

Quality rule suggestions can now be reviewed with the same local actions used by the rest of the workbench:

- `accept` confirms the suggested expression and severity
- `edit` confirms reviewed `rule_expression` and `severity`
- `reject` excludes the suggestion from confirmed rules
- `mark_for_manual_review` keeps the decision auditable but excludes the rule from confirmed output in this version

Confirmed rules are persisted through quality rule review records in `app/data/overrides/quality_rule_overrides.csv` and replayed into `confirmed_quality_rules` during review-enabled quality workflows.

Reference document:

- `docs/quality_rule_review_and_export_spec.md`

## Rule Export Adapter

Confirmed quality rules can be exported as rule assets for future execution engines:

- custom JSON rules package
- first-version dbt tests YAML

The dbt adapter focuses on a stable, extensible structure. It maps simple rules such as `not_null`, `uniqueness`, and `value_set`, while range, regex, and format rules are carried as metadata placeholders for later native or custom test mapping.

## Execution-Ready Governance Package

Confirmed quality rules can now be standardized into an `execution_ready_package`. This package is an intermediate execution contract, not a runtime executor.

The package adds:

- deterministic `rule_id`
- target table and field metadata
- semantic type and execution expression
- execution mode and engine hints
- severity, priority, and confirmation metadata
- package-level compatibility hints

Reference document:

- `docs/execution_ready_package_spec.md`

## Execution Package Export Formats

Execution-ready packages can be exported as:

- package JSON
- package manifest JSON
- first-version dbt tests YAML

The package layer keeps rule assets decoupled from target engine formats. The dbt export is still a first-version adapter and does not cover the full native dbt test surface.

## Governance Delivery Package & Confirmation Workbook

The project can now generate reviewer-facing delivery artifacts for governance collaboration and manual confirmation.

Current delivery outputs include:

- standard mapping confirmation workbook
- STG structure confirmation workbook
- quality rule confirmation workbook
- remediation/backlog workbook
- governance delivery package manifest

The delivery package is generated as a local directory containing Excel workbooks and a JSON manifest. Reports can reference delivery summaries, but reports remain descriptive outputs while delivery packages are confirmation-oriented handoff artifacts.

Reference document:

- `docs/governance_delivery_package_spec.md`

## Batch Processing & Incremental Rerun

The project now supports multi-file governance batches and lightweight changed-only reruns. Batch input can be grouped by `system_name`, `schema_name`, or an inferred `domain_hint`.

The incremental mechanism stores local JSON snapshots under `app/data/batch_snapshots/` and compares table-level SHA-256 fingerprints between runs. Diff output classifies objects as `new`, `changed`, `unchanged`, `removed`, or `pending_review`, then changed-only rerun scopes processing to new, changed, and pending objects.

Reference document:

- `docs/batch_processing_and_incremental_rerun_spec.md`

## Workbook Import & Confirmation Round-Trip

Filled confirmation workbooks can now be imported back into the local governance workflow. The importer validates the workbook, normalizes column aliases and confirmation statuses, reports invalid or skipped rows, and merges valid decisions into local mapping/STG/quality review records or backlog status updates.

Supported workbook types include:

- `mapping_confirmation`
- `stg_confirmation`
- `quality_rule_confirmation`
- `backlog_confirmation`

The round-trip output includes import summaries, round-trip merge results, changed object keys, and a changed-only rerun scope.

Reference document:

- `docs/workbook_import_and_roundtrip_spec.md`

## Governance Readiness & Remediation Planning

The project can now consolidate diagnosis, mapping, STG, quality intelligence, confirmed rules, execution packages, and review queues into governance decision support.

Current outputs include:

- table-level `readiness_scores`
- classified `governance_gaps`
- prioritized `remediation_actions`
- exportable `governance_work_package`

Readiness is scored across metadata readiness, standardization readiness, structural readiness, quality rule readiness, and review completion readiness. Gap classification turns missing metadata, mapping defects, low-confidence STG or quality signals, and review backlog into owner-oriented remediation actions.

Reference document:

- `docs/governance_readiness_and_remediation_spec.md`

## Governance Backlog & Tracking

Remediation actions can now be converted into `governance_backlog_items` so the local workflow can track what needs to be handled after a readiness and gap assessment.

Each backlog item carries a deterministic `backlog_id`, object and gap identity, owner role hint, priority, lifecycle status, urgency score, dependency notes, completion criteria, expected output, source signals, timestamps, and notes.

Current status values are:

- `proposed`
- `accepted`
- `in_progress`
- `blocked`
- `completed`
- `dropped`

Current priorities are:

- `priority_governance`
- `key_tracking`
- `continuous_observation`

Backlog state is stored locally in JSON under `app/data/governance_backlog/`, with snapshots created before overwrites. It is available through workflow profiles, intent interpretation, tools, adapter schemas, reports, API routes, and the Streamlit `Governance Backlog` page.

Reference document:

- `docs/governance_backlog_tracking_spec.md`

## Governance Portfolio & Progress Dashboard

The project can now summarize backlog tracking into a governance portfolio view. The portfolio layer adds SLA-ready due dates, backlog aging, overdue analysis, owner workload, readiness distribution, and progress snapshots.

Current outputs include:

- `backlog_sla_statuses`
- `governance_portfolio_summary`
- `progress_snapshot`

The SLA layer infers due dates from priority and owner role policies in `backlog_sla_policies.yaml`. The portfolio summary aggregates backlog items by status, priority, owner role, and gap type, and adds overdue count, blocked count, owner workload, and readiness level distribution. Progress snapshots are local JSON point-in-time records for trend-ready exports.

Reference document:

- `docs/governance_portfolio_and_progress_spec.md`

## Human-in-the-Loop Review

The project includes a local review workbench that supports:

- `accept`
- `reject`
- `edit`
- `mark_for_manual_review`

Review currently applies to:

- standard mapping recommendations
- STG field structure suggestions
- quality rule suggestions

Confirmed review records are persisted locally under:

- `app/data/overrides/`
- `app/data/review_history/`

Reference document:

- `docs/review_override_spec.md`

## Override Memory

Saved overrides are reused in later review-enabled runs. When a matching key is found:

- mapping overrides are applied before confirmed mapping results are returned
- STG overrides are applied before confirmed STG suggestions are returned
- quality rule overrides are applied before confirmed quality rules are returned
- confirmed results can then be exported as separate report sections and sheets

## Workflow Profiles

The router currently supports these named workflow profiles:

- `metadata_diagnosis_only`
  - quick diagnosis scan only
- `diagnosis_plus_mapping`
  - diagnosis plus standard field recommendation
- `diagnosis_mapping_stg`
  - diagnosis, mapping, and STG structure suggestion
- `diagnosis_mapping_stg_with_review`
  - diagnosis, mapping, STG, and replay of saved review overrides
- `diagnosis_mapping_stg_quality`
  - diagnosis, mapping, STG, and quality rule recommendation
- `diagnosis_mapping_stg_quality_with_review`
  - diagnosis, mapping, STG, quality rule recommendation, and replay of saved review overrides
- `diagnosis_mapping_stg_quality_package`
  - diagnosis, mapping, STG, quality rule recommendation, and execution package build
- `diagnosis_mapping_stg_quality_package_with_review`
  - diagnosis, mapping, STG, quality rule recommendation, quality review replay, and execution package build
- `governance_readiness_assessment`
  - diagnosis, mapping, STG, quality intelligence, execution package build, readiness scoring, gap classification, and remediation planning
- `governance_readiness_assessment_with_review`
  - readiness assessment with saved review replay before confirmed quality and package outputs
- `full_governance_work_package`
  - full chain through quality review, confirmed rules, execution package, readiness assessment, gap classification, and remediation planning
- `governance_backlog_build`
  - readiness assessment, remediation planning, and local governance backlog item generation
- `governance_backlog_build_with_review`
  - review-enabled readiness and remediation chain with backlog generation
- `full_governance_backlog_package`
  - full governance work package plus local backlog build for tracking and export
- `governance_portfolio_assessment`
  - backlog build plus SLA analysis, portfolio aggregation, and progress snapshot
- `full_governance_portfolio_package`
  - full governance backlog package plus portfolio summary and progress snapshot outputs
- `mapping_only`
  - standard mapping only
- `stg_only_from_mapping`
  - mapping and STG suggestion without full diagnosis packaging
- `quality_only_from_stg`
  - mapping, STG suggestion, and quality rule recommendation without full diagnosis packaging
- `quality_only_from_stg_with_review`
  - mapping, STG suggestion, quality rule recommendation, and quality review replay without full diagnosis packaging
- `quality_package_only_from_confirmed`
  - mapping, STG suggestion, quality review replay, and execution package build without full diagnosis packaging

Reference document:

- `docs/workflow_profile_spec.md`

## Governance Task Router

The project includes a unified governance task entrypoint that routes a structured request to the correct workflow profile.

This layer is intended to become the stable execution base for:

- Streamlit profile-based runs
- unified API invocation
- future agent or planner integration

## Intent Interpreter

The project includes a rule-based intent interpreter that converts short natural-language governance requests into a standard `GovernanceTaskRequest`.

This layer:

- uses configurable keyword matching
- maps task text to a workflow profile
- infers simple parameters such as `export_reports` and `apply_review_replay`
- falls back safely to `metadata_diagnosis_only` when intent is unclear

Reference document:

- `docs/intent_interpreter_spec.md`

## Supported Intent Types

- `quick_scan`
- `standard_recommendation`
- `structure_suggestion`
- `quality_rule_recommendation`
- `confirmed_quality_rules`
- `execution_ready_package`
- `governance_readiness_assessment`
- `full_governance_work_package`
- `replay_confirmed`
- `mapping_only_request`
- `stg_only_request`
- `quality_only_request`

## Context Resolver

The project includes a rule-based context resolver that can:

- reuse the current session's last uploaded file
- reuse the last task file when the request refers to a previous file
- reuse the last exported report directory when export context is available
- surface ambiguity instead of guessing when multiple file candidates conflict

Reference document:

- `docs/context_resolver_spec.md`

## Agent Shell v1

The project includes a lightweight agent shell that can:

- interpret natural language
- resolve missing context parameters
- build an execution plan
- validate required parameters
- preview before run
- require confirmation for selected profiles
- execute after confirmation or explicit force run

Reference document:

- `docs/agent_shell_spec.md`

## Tool Contract Layer

The project includes a standard local tool contract layer that exposes current governance capabilities through named tools with explicit input and output schema metadata.

This layer is intended to be the stable invocation surface for:

- future agent adapters
- future tool-calling adapters
- local debugging and replay
- execution audit and trace review

Reference document:

- `docs/tool_contract_spec.md`

## Available Tools

- `run_governance_profile`
- `interpret_governance_intent`
- `preview_agent_plan`
- `run_agent_task`
- `resolve_governance_context`
- `export_governance_reports`
- `recommend_quality_rules`
- `recommend_quality_intelligence`
- `review_quality_rules`
- `batch_review_quality_rules`
- `export_confirmed_quality_rules`
- `build_execution_ready_package`
- `export_execution_ready_package`
- `assess_governance_readiness`
- `build_governance_work_package`
- `list_config_assets`
- `get_config_asset`
- `validate_config_asset`
- `save_config_asset`
- `publish_config_asset`

## Adapter Layer v1

The project includes a lightweight adapter-ready layer that sits on top of the
local tool contract surface.

Current adapter capabilities:

- capability manifest generation
- native tool schema export
- openai-style function schema export
- mcp-style lightweight manifest export
- local invocation adapter for alternate input shapes
- confirmed quality rule export through the local rule export adapter
- execution-ready package build and export through the local package adapter path
- readiness and remediation work-package build through the local tool/adapter path
- governance backlog build, list, status update, and schema export through the local tool/adapter path
- governance portfolio assessment and progress snapshot generation through the local tool/adapter path

Reference document:

- `docs/adapter_layer_spec.md`

## Export Formats

Current adapter exports support:

- native tool schema
- openai-style function schema
- mcp-style lightweight manifest
- custom JSON confirmed quality rule package
- execution-ready package JSON
- execution-ready package manifest JSON
- governance work package JSON
- governance backlog items and backlog summary in JSON / Markdown / Excel reports
- backlog SLA statuses, governance portfolio summary, and progress snapshot in JSON / Markdown / Excel reports
- first-version dbt tests YAML

## Governance Control Plane

The project includes a lightweight local control plane for the most important
governance configuration assets.

Managed assets currently include:

- `abbreviation_dict`
- `root_word_dict`
- `standard_fields`
- `workflow_profiles`
- `intent_patterns`
- `tool_registry`
- `quality_rule_templates`
- `quality_rule_policies`
- `execution_package_policies`
- `rule_execution_templates`
- `domain_rule_templates`
- `cross_field_rule_patterns`
- `quality_review_policies`
- `readiness_scoring_policies`
- `governance_gap_taxonomy`
- `remediation_templates`
- `governance_backlog_policies`
- `backlog_status_templates`
- `governance_portfolio_policies`
- `backlog_sla_policies`
- `progress_snapshot_policies`

This layer supports:

- view and inspect current asset content
- basic validation before save or publish
- local backup creation before overwrite
- lightweight `draft` / `published` / `invalid` status tracking
- direct access from both Streamlit and the standardized tool layer

Reference document:

- `docs/control_plane_spec.md`

## Execution Trace

Each tool call generates a local execution trace that records:

- tool name
- session id when available
- raw text when available
- profile name when available
- summarized inputs
- resolved context summary
- stages executed
- status and message
- config asset name and operation when the call targets control-plane tools
- validation status for config asset actions when available
- exported files when available
- quality rule export format and exported rule counts when rule assets are exported
- execution package id, package rule count, export format, and exported package path when package assets are exported
- field-level rule count, cross-field rule count, low-confidence rule count, and review queue summary when quality intelligence is used
- readiness score count, gap count, remediation action count, and work package name when readiness/remediation tools run
- backlog item count, backlog status summary, updated backlog id, and old/new status when backlog tools run
- overdue count, blocked count, owner workload summary, and snapshot id when portfolio or progress tools run

Adapter-layer invocations reuse the same underlying tool traces, so external
integration preparation still stays auditable through the existing local trace store.

Traces are stored locally and are intended for audit, debugging, and replay analysis.

## Local Workflow

The local workflow is:

1. upload metadata file
2. optionally enter a natural-language governance task
3. interpret it into a workflow profile or select a profile directly
4. optionally let the context resolver autofill missing parameters such as `file_path`
5. optionally preview the execution plan in Agent Shell
6. optionally invoke the standardized tool layer directly
7. run the governance task
8. inspect issues, tasks, mapping results, STG suggestions, and quality rule recommendations
9. review, accept, reject, edit, or mark suggestions for manual review
10. rerun with saved overrides
11. confirm quality rules and build the execution-ready package when needed
12. assess readiness, classify gaps, and build the governance work package
13. build governance backlog items from remediation actions
14. assess SLA, owner workload, overdue risk, and governance portfolio summary
15. save a local progress snapshot when a point-in-time record is needed
16. persist, filter, and update local backlog status when tracking is needed
17. optionally run multi-file batch processing or changed-only incremental rerun
18. import filled confirmation workbooks and merge reviewer decisions
19. build confirmation workbooks and a local governance delivery package
20. export rule assets, package assets, work-package assets, backlog outputs, portfolio outputs, delivery assets, and confirmed reports
21. maintain dictionaries, profiles, intent patterns, tool registry, backlog policies, portfolio policies, delivery policies, batch policies, and workbook import policies through Control Plane when needed
22. inspect capability manifest or adapter schemas before future external integration work

In Streamlit, use the pages in this order:

1. `Upload`
2. `Intent Runner` or `Agent Shell` or `Diagnosis`
3. `Review`
4. `Quality Rules`
5. `Execution Package`
6. `Governance Readiness`
7. `Governance Backlog`
8. `Governance Portfolio`
9. `Governance Delivery`
10. `Batch & Incremental Rerun`
11. `Confirmation Import`
12. `Reports`
13. `Tool Console`
14. `Control Plane`
15. `Adapter Console`

## Suggested Governance Chain

Recommended local governance flow:

`export workbook -> external confirmation -> import workbook -> merge updates -> rerun changed objects`

## Current Boundary

- current quality output is rule-based field-level, domain-aware, and cross-field recommendation plus confirmed rule asset and execution-ready package export, not rule execution
- current dbt export is a first-version adapter and does not cover the full native dbt test surface
- current dbt export carries cross-field rules as compatibility metadata when they are not native tests
- current package/export adapters do not run or export complete Great Expectations or Soda runtime configurations
- current cross-field/domain-aware logic is metadata-template based and does not perform statistics-aware discovery
- current rule export does not call dbt, a database, or any external runtime
- current readiness/remediation output is decision support and work-package export only; it does not assign owners, create tickets, or execute governance actions
- current backlog support covers local backlog generation, JSON/CSV-ready tracking state, filtering, status updates, summary, and report export
- current backlog support does not auto-assign work or connect to Jira, Feishu, DingTalk, TAPD, or other external project management systems
- current portfolio support covers local portfolio summary, SLA-ready metadata, overdue analysis, owner workload, and progress snapshots
- current portfolio support does not connect to external PM systems, BI platforms, or automatic reminder services
- current delivery support exports local confirmation workbooks and delivery package manifests only
- current delivery support does not connect to external distribution systems or automatically send files
- current incremental support uses local snapshots and object fingerprints only
- current incremental support does not perform complex semantic diff, realtime folder watching, or automatic scheduling
- current workbook round-trip supports local workbook import and merge only
- current workbook round-trip does not perform multi-user conflict resolution or collaborative merge

## Future Extensions

- Great Expectations adapter
- Soda checks adapter
- statistics-aware rule mining
- domain-specific policy packs
- cross-table constraints
- execution orchestrator and result ingestion
- domain-aware execution policy
- JIRA-ready export
- owner assignment integration
- progress dashboard
- SLA / due-date policies
- dashboard UI
- due-date policy tuning
- project management adapters
- governance KPI tracking
- multi-domain governance portfolio
- zip packaging
- email / SharePoint delivery adapter
- domain-specific delivery templates
- folder watch
- semantic diff
- scheduler integration
- domain batch templates
- template versioning
- collaborative merge policies
- email / SharePoint intake adapter

## Project Layout

```text
app/
  api/        FastAPI routes
  core/       parsers, workflow, skills, knowledge, normalize, models, reporters, utilities
  data/       sample inputs, governance dictionaries, standard libraries, overrides, and audit traces
  ui/         Streamlit workbench
docs/         project notes and specifications
outputs/      uploaded files, agent snapshots, and exported reports
tests/        pytest coverage for local MVP flows
```

## Run Instructions

Install dependencies:

```bash
pip install -r requirements.txt
```

Run FastAPI:

```bash
uvicorn app.main:app --reload
```

Useful endpoints:

- `GET /health`
- `POST /jobs/run-p0-demo`
- `POST /jobs/run-p0-from-file`
- `POST /jobs/run-p0-plus-mapping`
- `POST /jobs/run-p0-plus-mapping-plus-stg`
- `POST /jobs/run-p0-plus-mapping-plus-stg-with-review`
- `POST /jobs/run-p0-plus-mapping-plus-stg-plus-quality`
- `POST /jobs/run-p0-plus-mapping-plus-stg-plus-quality-with-review`
- `POST /jobs/run-mapping-only`
- `POST /jobs/run-stg-only-from-mapping`
- `POST /jobs/run-quality-only-from-stg`
- `POST /jobs/run-quality-only-from-stg-with-review`
- `POST /jobs/run-governance-task`
- `GET /jobs/list-workflow-profiles`
- `POST /jobs/interpret-governance-task`
- `POST /jobs/run-interpreted-governance-task`
- `POST /jobs/agent-shell/plan`
- `POST /jobs/agent-shell/resolve-context`
- `POST /jobs/agent-shell/run`
- `GET /jobs/agent-shell/session/{session_id}`
- `GET /jobs/list-tools`
- `POST /jobs/call-tool`
- `GET /jobs/capability-manifest`
- `GET /jobs/tool-schemas/native`
- `GET /jobs/tool-schemas/openai`
- `GET /jobs/tool-schemas/mcp`
- `POST /jobs/invoke-native-tool`
- `POST /jobs/invoke-openai-tool`
- `GET /jobs/trace/{trace_id}`
- `GET /jobs/traces/recent`
- `GET /jobs/config-assets`
- `GET /jobs/config-assets/{asset_name}`
- `POST /jobs/config-assets/{asset_name}/validate`
- `POST /jobs/config-assets/{asset_name}/save`
- `POST /jobs/config-assets/{asset_name}/publish`
- `POST /jobs/save-mapping-review`
- `POST /jobs/save-stg-review`
- `GET /jobs/list-review-summary`
- `POST /jobs/review-quality-rules`
- `POST /jobs/export-confirmed-quality-rules`
- `POST /jobs/build-execution-ready-package`
- `POST /jobs/export-execution-ready-package`
- `POST /jobs/assess-governance-readiness`
- `POST /jobs/build-governance-work-package`
- `GET /jobs/governance-readiness-summary`
- `GET /jobs/execution-package-summary`
- `GET /jobs/quality-rule-review-summary`

Example request body for file-based execution:

```json
{
  "file_path": "D:/Projects/data_governance_skills/app/data/samples/sample_metadata.csv"
}
```

Run Streamlit:

```bash
streamlit run app/ui/streamlit_app.py
```

Run tests:

```bash
pytest
```

## Current Capability Boundary

The current version supports:

- knowledge-pack-driven naming enhancement
- rule-based standard mapping recommendation
- rule-based STG structure suggestion
- human-in-the-loop review, override persistence, and confirmed result export
- confirmed quality rule review and rule asset export
- domain-aware and cross-field quality rule recommendation with confidence and review priority
- execution-ready governance package build and package asset export
- governance readiness scoring, gap classification, and remediation work-package export
- workflow profile routing and unified governance task execution
- rule-based natural-language intent interpretation
- rule-based context resolution and parameter autofill
- agent shell plan preview, validation, and confirmation-aware execution
- standard tool contract layer with unified local tool execution
- local execution trace storage for audit and replay
- governance control plane with managed asset validation and publish status
- adapter layer with capability manifest and schema export
- rule-based P0 diagnosis and task packaging
- local report export

## Output Artifacts

Current exported artifacts can include:

- diagnosis issues
- governance tasks
- standard mapping recommendations
- STG structure suggestions
- confirmed standard mapping
- confirmed STG suggestions
- confirmed quality rules
- cross-field quality rules
- quality review queue summary
- quality rule review summary
- custom JSON and dbt YAML rule export results
- execution-ready package JSON, manifest, and dbt YAML export results
- readiness scores, governance gaps, remediation actions, and governance work package
- review summary
- tool execution traces

It intentionally does not support:

- LLM reasoning
- embedding or vector retrieval
- semantic retrieval services
- agent orchestration or routing
- direct database integration
- database, queue, async job, Docker, or CI setup

Current boundary notes:

- current STG output is a structure suggestion, not a DDL generator
- current STG logic does not handle complex split or merge rules
- current STG suggestions still require manual confirmation
- current review mechanism is local single-user only
- current review mechanism does not support approval flow, permissions, or database persistence
- current workflow router is rule-based and depends on explicit profile selection
- current intent interpreter is rule-based keyword matching only
- current intent interpreter is not LLM-based
- current intent interpreter does not support multi-turn dialogue
- current context resolution is rule-based and session-scoped
- current context resolution does not perform complex file search or semantic reference resolution
- current agent shell is rule-based and preview-first
- current agent shell does not include LLM planning or autonomous replanning
- current tool contract layer is a local executor only
- current tool contract layer does not implement MCP, OpenAI tool calling, or any external runtime adapter
- current rule export creates assets only and does not execute rules
- current execution-ready package creates a contract only and does not execute rules or schedule jobs
- current remediation planning creates recommended actions only and does not create tickets, assign work, or update external project systems
- current adapter layer is local and preparation-oriented only
- current adapter layer is not a formal MCP server
- current adapter layer is not an OpenAI SDK integration
- current control plane is local single-user only
- current control plane does not support approval flow, permissions, or database-backed version management
- current workflow router does not support natural-language intent recognition beyond the configured interpreter
- current workflow router is not a fully autonomous agent system

## Suggested Workflow

Recommended user flow:

1. upload metadata file
2. either type a natural-language task or choose a workflow profile
3. optionally leave `file_path` blank and let the context resolver reuse the current session file
4. preview the plan in Agent Shell when you want validation or confirmation control
5. optionally call the standardized tool layer for repeatable execution
6. run the governance task
7. open the Review page
8. save `accept`, `reject`, `edit`, or `mark_for_manual_review` decisions
9. rerun with overrides
10. open Quality Rules to confirm and export quality rule assets
11. open Execution Package to build and export package assets
12. open Governance Readiness to build readiness scores and remediation actions
13. export confirmed outputs and governance work packages
14. inspect traces for audit and replay analysis
15. use Control Plane to maintain core dictionaries and routing configuration safely

## Suggested Usage Modes

- quick scan -> `metadata_diagnosis_only`
- standard recommendation -> `diagnosis_plus_mapping`
- structure suggestion -> `diagnosis_mapping_stg`
- replay confirmed decisions -> `diagnosis_mapping_stg_with_review`
- confirmed quality rules -> `diagnosis_mapping_stg_quality_with_review`
- quality intelligence -> `diagnosis_mapping_stg_quality`
- execution-ready package -> `diagnosis_mapping_stg_quality_package_with_review`
- readiness assessment -> `governance_readiness_assessment_with_review`
- full remediation work package -> `full_governance_work_package`
- governance backlog tracking -> `governance_backlog_build`
- full governance backlog package -> `full_governance_backlog_package`
- governance portfolio assessment -> `governance_portfolio_assessment`
- full governance portfolio package -> `full_governance_portfolio_package`
- mapping validation only -> `mapping_only`
- STG validation only -> `stg_only_from_mapping`
- tool-layer debugging -> `Tool Console`
- configuration maintenance -> `Control Plane`
- integration preparation -> `Adapter Console`

## Autofill Behavior

Current autofill priority is:

1. explicit `file_path`
2. current session `last_uploaded_file_path`
3. current session `last_task_request.file_path`
4. sample fallback only when configuration explicitly enables it

Safety rules:

- explicit input always wins
- a single safe candidate may be autofilled
- ambiguous candidates are not guessed
- ambiguity is surfaced in the execution plan and returned result

## Example Requests

For a quick local demo, use `app/data/samples/sample_metadata.csv` and try:

- `Help me inspect this file`
- `Use the uploaded file for standard mapping and export reports`
- `Generate STG structure suggestions from the last file`
- `Rerun with confirmed results and export reports`
- `Inspect the current uploaded metadata file`
- `Use the previous file to generate STG suggestions`
- `Preview the plan before running`
- edit mapping for `Sales Order Header.Order__ID`
- edit STG field for `ods_customer_snapshot.snapshot_dt`
- mark `user_audit_log.event_trace_code` for manual review

## Notes

The current parser, workflow, report, and tool layers are intentionally simple:

- parsing validates required columns and groups rows by `table_name`
- workflow orchestration keeps the existing P0 path stable and adds mapping and STG suggestion as optional extensions
- exporting writes local `.json`, `.md`, and `.xlsx` files under `outputs/`
- the tool layer wraps existing services instead of replacing them
- execution traces are local JSON audit files, not database records

## Suggested Next Steps

Natural follow-up directions for this adapter-ready layer are:

- MCP transport layer
- OpenAI tool-calling adapter
- external runtime integration

This keeps the project ready for later semantic or agent-based upgrades without changing the current P0 core behavior.

# Execution-Ready Governance Package Spec

## Purpose

Confirmed quality rules are reviewed rule assets, but they are still close to the review workbench. An execution-ready governance package adds a stable intermediate contract between reviewed rules and downstream execution engines.

This layer exists so the project can prepare for Great Expectations, Soda, dbt tests, custom rule runtimes, or a governance platform rule center without coupling confirmed rules to any one target format.

## Relationship to Confirmed Quality Rules

`confirmed_quality_rules` are the human-reviewed output of quality rule recommendation. They preserve the source table, source field, rule type, expression, severity, priority, confirmation source, match basis, reason, and notes.

The execution-ready package is built only from confirmed rules in the current policy. It enriches each confirmed rule with:

- a stable rule identity
- execution semantics
- execution mode hints
- engine compatibility hints
- trace metadata

Rejected and manual-review rules are excluded from the package.

## Relationship to Export Adapters

Export adapters should read the execution-ready package first. Target-specific formats such as package JSON, package manifest, or first-version dbt YAML are projections of the package.

Confirmed rules can still be exported for backward compatibility, but the preferred path is:

`confirmed_quality_rules -> execution_ready_package -> export adapter`

## Contract, Not Runtime

The package is not a rule executor. It does not connect to databases, schedule jobs, run SQL, call dbt, call Soda, or call Great Expectations.

It defines the execution contract that a future runtime can consume.

## Package Contents

Each execution-ready rule includes these groups of fields:

- Rule identity: `rule_id`, `rule_type`
- Target object: `source_table_name`, `source_field_name`, optional `target_field_name`
- Rule semantics: `semantic_type`, `rule_expression`, `execution_expression`
- Execution hints: `execution_mode`, `engine_hints`
- Governance ranking: `severity`, `priority`
- Confirmation metadata: `confirmation_source`, `match_basis`, `reason`, `notes`
- Trace metadata: package build context and optional caller-provided trace metadata
- Export compatibility hints: package-level `compatibility` and per-rule `engine_hints`

## Current Boundary

The current implementation builds local, rule-based, explainable packages only.

It does not execute rules, generate scheduler tasks, build cross-table execution plans, or integrate with external APIs. Cross-field rules, Great Expectations/Soda package adapters, and real execution runtimes are future extensions.

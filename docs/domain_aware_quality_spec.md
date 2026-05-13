# Domain-Aware Quality Intelligence Spec

## Purpose

Field-level quality rules are useful, but real governance review often depends on relationships between fields and on domain expectations. A transaction table needs amount/date/currency consistency. A status table often has code/name pairs. A customer domain usually expects identifiers and names to appear together.

Domain-aware and cross-field rules make quality rule assets closer to production governance artifacts while keeping the system rule-based and explainable.

## Relationship to Field-Level Rules

Field-level rules remain the base recommendation layer. They describe one field at a time, such as `not_null`, `uniqueness`, `value_set`, `numeric_range`, `date_format`, `length_range`, or `regex_format`.

Cross-field and domain-aware rules are added beside those rules. They use metadata, mapping, STG names, and configured templates to recommend rules about a group of fields in one source table.

The output therefore has two related layers:

- `quality_rule_suggestions`: field-level rules
- `cross_field_quality_rules`: single-table multi-field hints and constraints

Both can be reviewed, confirmed, packaged, and exported.

## Supported Cross-Field Patterns

Current rule patterns are rule-based and metadata-driven:

- `temporal_order`
  - `start_date <= end_date`
  - `created_date <= updated_date`
- `paired_presence`
  - `amount -> currency`
  - `status_code -> status_name`
  - `id -> name` as an advisory hint
- `conditional_presence_hint`
  - when a main business identifier exists, key time fields should also exist
  - when transaction amount exists, transaction date should also exist
- `reference_consistency_hint`
  - code/name pairs
  - id/code pairs

## Supported Domain Templates

Current domain templates include:

- `customer`
  - identifier/name group presence hints
- `transaction`
  - amount/currency pairing
  - transaction date presence
- `status`
  - code/name pairing

The templates are configured in `app/config/domain_rule_templates.yaml`.

## Confidence And Review Priority

`confidence` describes why the system believes a rule recommendation is strong. It is not a statistical score. It is a deterministic score from the configured confidence policy:

- exact template match
- domain token match
- STG name match
- source token match
- weak hint match

`review_priority` tells the local review workbench what should be looked at first:

- `high_review_priority` for low-confidence or sensitive reference hints
- `medium_review_priority` for cross-field rules that deserve human review
- `manual_review_preferred` for advisory reference consistency hints
- `standard_review_priority` for normal review

## Current Boundary

This is rule-based recommendation only. The project does not execute cross-field rules, connect to external engines, mine statistical distributions, or build cross-table lineage plans in this version.

Future extensions can add statistics-aware discovery, domain-specific governance packs, and runtime validation engine integration.

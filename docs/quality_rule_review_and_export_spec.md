# Quality Rule Review and Export Spec

## Purpose

Quality rule recommendation is intentionally rule-based and explainable, but a recommendation is not yet an approved governance asset. Review is required because rule templates can be too broad, source metadata can be incomplete, and business-owned fields may need stricter or softer thresholds than the default recommendation.

This layer turns suggested quality rules into confirmed quality rules through local, auditable review replay. It keeps recommendation logic separate from human decisions so the same input can be rerun with the same override records.

## Review, Override, and Confirmed Rules

- **Suggested rules** are produced by `quality_rule_recommendation`.
- **Review records** capture human decisions for a specific `source_table_name + source_field_name + rule_type`.
- **Overrides** are persisted review records stored in `app/data/overrides/quality_rule_overrides.csv`.
- **Confirmed quality rules** are the accepted or edited rules after replaying saved review records.

The review service is the boundary between suggestion and confirmation. The recommendation skill continues to generate candidates; the review service applies saved decisions and builds confirmed results.

## Supported Review Actions

- `accept`: keep the suggested rule expression and severity.
- `reject`: exclude the rule from `confirmed_quality_rules`.
- `edit`: use the reviewed `final_rule_expression` and/or `final_severity`.
- `mark_for_manual_review`: exclude the rule from confirmed output in this version and keep it visible in review summary counts.

## Confirmed Quality Rule Structure

Each confirmed rule contains:

- `source_table_name`
- `source_field_name`
- `recommended_field_name`
- `rule_type`
- `rule_expression`
- `severity`
- `priority`
- `confirmation_source`
- `match_basis`
- `reason`
- `notes`

Confirmed rules are deduplicated by `source_table_name + source_field_name + rule_type`.

## Export Formats

### Custom JSON Rules Package

The JSON adapter exports a portable package:

```json
{
  "generated_at": "...",
  "rule_count": 1,
  "rules": [
    {
      "table": "sales_order",
      "field": "order_id",
      "rule_type": "not_null",
      "rule_expression": "not_null",
      "severity": "high",
      "priority": "P1",
      "reason": "Matched rule template from standard mapping"
    }
  ]
}
```

### dbt Tests YAML

The dbt adapter emits a first-version YAML structure grouped by table and field. Native-friendly mappings include:

- `not_null` -> `not_null`
- `uniqueness` -> `unique`
- `value_set` -> `accepted_values`

Rules such as `length_range`, `numeric_range`, `date_format`, and `regex_format` are represented as metadata placeholders so they can be converted to native dbt tests or custom macros later.

## Current Boundary

This version does not execute quality rules. It does not connect to dbt runtime, Great Expectations, Soda, databases, external APIs, LLMs, embeddings, or vector stores. The output is a confirmed rule asset package that can be handed to an execution engine in a later phase.

## Future Extensions

- Great Expectations adapter
- Soda adapter
- Cross-field and table-level rule export
- Runtime execution integration and result ingestion

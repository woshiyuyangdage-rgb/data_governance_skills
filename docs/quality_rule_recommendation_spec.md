## Quality Rule Recommendation

This skill extends the existing governance chain from diagnosis, standard mapping, and STG structure suggestion into actionable data quality rule recommendations.

### Positioning

- `diagnosis` identifies metadata problems.
- `standard_mapping_recommendation` aligns fields to standard definitions.
- `stg_structure_suggestion` proposes normalized target structures.
- `quality_rule_recommendation` converts those governance hints into field-level quality rule suggestions.

### Inputs

The skill can use several upstream result layers, with a clear fallback order:

1. confirmed mapping results
2. standard mapping results
3. confirmed STG field suggestions
4. STG field suggestions
5. source field names and data types

### Recommended Rule Types

Current v1 recommendation coverage is field-level and rule-based:

- `not_null`
- `uniqueness`
- `value_set`
- `length_range`
- `numeric_range`
- `date_format`
- `regex_format`
- `reference_hint`

### Recommendation Logic

The skill uses standard codes, recommended STG field names, source field names, tokens, and data types to match rule templates.

Examples:

- identifier fields such as `customer_id` or `order_id`
  - recommend `not_null`
  - recommend `uniqueness`
- amount fields such as `transaction_amount` or `balance`
  - recommend `numeric_range`
- date fields such as `created_date` or `snapshot_dt`
  - recommend `date_format`
- code or status fields
  - recommend `value_set`

### Output Structure

The skill returns:

- `quality_rule_suggestions`
  - flat field-level rule recommendations
- `quality_rule_packages`
  - grouped per source table for downstream review and export
- `issues`
  - low-confidence or no-rule findings
- `summary`
  - readable recommendation overview

### Human Review Points

This skill is recommendation-oriented, not execution-oriented. Users should review:

- whether `not_null` is truly mandatory for the field
- whether `uniqueness` applies at row level
- whether `value_set` needs a maintained reference list
- whether `numeric_range` and `length_range` need domain thresholds
- whether regex and reference hints should be promoted into executable rules

### Current Boundary

- rule-based recommendation only
- no rule execution
- no Great Expectations, Soda, or dbt test generation
- no cross-table or complex cross-field constraints
- no LLM or external domain engine

### Extension Direction

Future versions can add:

- export adapters for external rule engines
- configurable domain-specific thresholds
- cross-field and reference-aware rule generation
- confirmed quality-rule overrides and feedback memory

# Review and Override Specification

## 1. Review Positioning

The current review layer turns metadata governance from a recommendation-only workflow into a confirm-and-reuse workflow.

The goal is to let a user:

1. inspect suggested mapping and STG results
2. accept or correct them
3. persist local overrides
4. rerun the workflow with override memory applied

## 2. Supported Review Objects

The current version supports review for:

1. standard mapping recommendations
2. STG field structure suggestions

Table-level STG review is represented indirectly through field-level review and issue flags.

## 3. Supported Review Actions

Supported actions are:

1. `accept`
   - keep the current recommendation and mark it as confirmed
2. `reject`
   - reject the current recommendation and force fallback or manual handling
3. `edit`
   - overwrite the current recommendation with a user-provided value
4. `mark_for_manual_review`
   - keep the suggestion visible but force a review flag

## 4. Override Storage

Overrides are stored locally under:

- `app/data/overrides/`
- `app/data/review_history/`

Current active override files:

- `mapping_overrides.csv`
- `stg_overrides.csv`

History snapshots are written into:

- `app/data/review_history/review_sessions/`

## 5. Override Reuse

When a review-enabled workflow is executed:

1. existing override files are loaded
2. matching keys are applied to current mapping or STG suggestions
3. confirmed results are returned alongside raw recommendations

Current key design:

- mapping key: `table_name + field_name`
- STG key: `source_table_name + source_field_name`

## 6. Current Boundary

The current version is intentionally limited:

- local single-user review only
- no approval flow
- no version conflict handling
- no database persistence
- no multi-user coordination

## 7. Future Extension Notes

- TODO: add multi-user reviewer identity and audit metadata
- TODO: add approval states and lightweight workflow routing
- TODO: replace local files with database persistence when needed
- TODO: allow future agent workflows to reference human review history safely

## 8. Demo Review Path

For the built-in `sample_metadata.csv`, a simple local demo path is:

1. run diagnosis with standard mapping and STG enabled
2. edit mapping for `Sales Order Header.Order__ID`
3. edit STG field for `ods_customer_snapshot.snapshot_dt`
4. mark `user_audit_log.event_trace_code` for manual review
5. save review records and rerun with overrides
6. export confirmed mapping and confirmed STG outputs

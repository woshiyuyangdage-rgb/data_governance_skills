# Confirmation Workbook Template Profiles

## Why Workbook Template Profiles Are Needed

Confirmation workbooks are often edited or recreated by different business teams. Real projects may use simplified review sheets, department-specific column names, or reduced column sets while still carrying the same review decisions. Template profiles let the system recognize and import these structured confirmation files without requiring users to manually rename columns first.

## Workbook Template Versus Workbook Type

A workbook type describes the business purpose of the confirmation data, such as `mapping_confirmation`, `stg_confirmation`, `quality_rule_confirmation`, or `backlog_confirmation`.

A workbook template describes one concrete file layout for that type. Multiple templates can map to the same workbook type.

## Why Multiple Confirmation Versions Exist

Different teams may remove columns, localize headers, split review work by department, or use shorter business-facing names. These variations should still map into the same normalized review rows before round-trip merge.

## Current Template Profiles

- `standard_mapping_confirmation_template`
- `business_mapping_review_template`
- `stg_design_review_template`
- `quality_rule_review_template`
- `backlog_update_template`

## Template Diagnosis

Template diagnosis reads file headers, scores configured template profiles, identifies the best sheet, reports missing required fields, and lists unmapped source columns. This gives users an import recommendation before merge or rerun.

## Current Boundary

This phase uses local rule-based template recognition and column mapping for structured Excel/CSV files. It does not perform OCR, complex semantic template learning, LLM calls, embeddings, vector search, database persistence, or arbitrary free-form column inference.


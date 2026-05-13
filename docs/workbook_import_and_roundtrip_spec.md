# Workbook Import & Confirmation Round-Trip

## Why Confirmation Workbook Round-Trip Is Needed

Governance confirmation often happens outside the application in Excel. The delivery package can export confirmation workbooks, but the governance loop is incomplete unless reviewed workbooks can be imported back into the local system.

Workbook round-trip imports external reviewer decisions, validates rows, converts accepted/rejected/edited decisions into review records or updates, and identifies changed objects for focused rerun.

## Supported Workbook Types

The current version supports:

- `mapping_confirmation`
- `stg_confirmation`
- `quality_rule_confirmation`
- `backlog_confirmation`

## Import Behavior

Each workbook is imported from Excel. The importer detects the main sheet from configured candidates, normalizes column aliases, validates required columns, normalizes `confirmation_status`, and parses row-level reviewer notes and edited values.

Mapping rows become mapping review records. STG rows become STG review records. Quality rule rows become quality rule review records. Backlog rows become backlog status update requests.

## Import Summary

The import summary includes total, imported, skipped, invalid, accepted, rejected, edited, and manual-review counts.

Invalid rows are rows that cannot be converted because required values are missing or status values are unknown. Skipped rows are intentionally ignored rows, such as empty rows or `pending` rows.

## Current Boundary

This is a lightweight local round-trip mechanism. It validates workbook shape, imports row-level decisions, and writes local review/override/backlog updates.

It does not implement complex template version negotiation, collaborative conflict resolution, external form systems, databases, LLMs, embeddings, or vector stores.


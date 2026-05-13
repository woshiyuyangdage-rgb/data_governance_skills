# Batch Processing & Incremental Rerun

## Why Batch Processing Is Needed

Real governance work usually arrives as multiple metadata files from different systems, schemas, or business domains. Running each file manually creates repeated effort and makes it hard to compare which objects changed between governance cycles.

Batch processing lets the local workflow load multiple metadata files, group related tables, and summarize results at group and batch level while reusing the existing single-file governance chain.

## Why Incremental Rerun Is Needed

Most governance cycles only change a subset of metadata objects. Incremental rerun reduces repeated work by comparing the current metadata fingerprints with the latest local snapshot and selecting only new, changed, or still-pending objects for rerun.

## Batch Groups Versus Single-File Runs

A single-file run treats one uploaded metadata file as the execution unit.

A batch group treats related tables across one or more files as the execution unit. Current grouping supports `system_name`, `schema_name`, and a lightweight `domain_hint` inferred from metadata text.

## Incremental Judgment Basis

Incremental comparison is based on object-level fingerprints. The current version fingerprints table-level metadata and field-level metadata using a stable SHA-256 hash. The configured fingerprint policy controls which metadata fields participate in the hash.

This is intentionally lightweight and explainable. It does not perform semantic diff, data profiling, statistics-aware comparison, or database comparison.

## Diff Output

The diff output includes:

- `new`: object exists in the current run but not in the latest snapshot
- `changed`: object exists in both runs but fingerprint changed
- `unchanged`: object exists in both runs and fingerprint is unchanged
- `removed`: object existed in the latest snapshot but not in the current run
- `pending_review`: object is treated as requiring rerun because review or confirmation is still pending

The diff summary includes counts for each category and a short explanation.

## Current Boundary

This phase supports multi-file batch input, grouping, fingerprint comparison, changed/new/unchanged/pending summaries, local JSON snapshots, and changed-only rerun scope selection.

It does not include folder watching, realtime synchronization, external schedulers, databases, external APIs, LLMs, embeddings, vector stores, or complex semantic diff.


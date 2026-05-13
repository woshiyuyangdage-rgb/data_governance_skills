# Enterprise Delivery Adapters

## Why Enterprise Delivery Adapters Are Needed

The standard governance delivery package is useful as a system export, but real projects usually send role-specific workbooks with familiar sheet names, column labels, and bundle composition. Enterprise delivery adapters make those exported files closer to what business, architecture, quality, and governance teams expect to receive.

## Relationship to Governance Delivery Package

The existing governance delivery package remains the canonical local delivery flow. Delivery template profiles sit on top of it and adapt the presentation of confirmation workbooks or package bundles without changing the underlying governance semantics.

## Delivery Adapter Versus Report Export

Reports summarize workflow results for reading and audit. Delivery adapters create reviewer-facing artifacts intended for confirmation, handoff, and round-trip import. The adapter layer controls workbook layout and bundle variants, while reports remain descriptive outputs.

## Current Delivery Template Profiles

- `business_mapping_delivery_template`
- `architecture_stg_delivery_template`
- `quality_rule_review_delivery_template`
- `governance_backlog_delivery_template`
- `full_governance_delivery_bundle_template`

## Export Layout Specs

Layout specs define the sheet name, display column names, column order, and extra columns for a delivery template. They keep workbook adaptation rule-based and explainable.

## Project Delivery Bundle Variants

Bundle variants define which outputs should be included for a project scenario. For example, a business confirmation bundle can include mapping and quality review workbooks, while an architecture design bundle can focus on STG design plus execution-ready assets.

## Current Boundary

This phase supports local rule-based delivery adaptation for Excel, JSON, and Markdown outputs. It does not build a complex layout engine, Word/PPT generator, Office macro system, external distribution workflow, database integration, LLM integration, embeddings, or vector search.

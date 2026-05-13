# Enterprise Metadata Intake Adapters

## Why Intake Adapters Are Needed

Enterprise metadata often arrives from governance platforms, manual inventory workbooks, or confirmation workbooks. These exports rarely use the normalized column names required by the existing parser. Intake adapters let the system accept structured Excel/CSV files from different sources and normalize them into the standard metadata input shape before governance workflows run.

## Relationship With The Standard Loader

The existing loader remains the canonical parser for normalized metadata files. The intake adapter sits before it: it diagnoses the incoming template, maps source columns to target fields, normalizes values, and produces standard records compatible with `TableMeta` and `FieldMeta`.

## Intake Profile Definition

An intake profile describes one supported source template family. It defines supported file types, sheet candidates, required target fields, optional target fields, and the mapping spec used for column matching.

## Field Mapping Spec

A field mapping spec maps each normalized target field to acceptable source column names. Matching is rule-based and transparent: exact target-field headers score highest, configured aliases score next, and weak normalized matches are only used as a low-confidence hint.

## Template Diagnosis

Template diagnosis reads file headers, compares them against enabled profiles and mapping specs, identifies the best sheet, reports matched headers, missing required target fields, and warnings. It helps users understand whether a file can be safely normalized before workflow execution.

## Current Intake Profiles

- `standard_metadata_template`
- `governance_platform_export_template`
- `manual_inventory_template`
- `mapping_confirmation_template`
- `quality_rule_confirmation_template`

## Current Boundary

This phase supports structured Excel/CSV metadata tables. It uses local rule-based header matching and column mapping only. It does not perform OCR, image parsing, complex semantic header understanding, LLM calls, embeddings, vector search, database persistence, or external platform API integration.


# Domain Governance Packs & Project Templates

## Why Domain Governance Packs Are Needed

Generic governance workflows are useful, but real governance projects usually need domain defaults. Customer, transaction, reference code, and supply chain finance metadata often have different mapping priorities, quality rule expectations, owner roles, and delivery outputs.

Domain governance packs provide reusable, rule-based hints for these common contexts. They do not replace the existing workflow logic. They provide preferred standards, quality templates, cross-field patterns, remediation hints, owner roles, and delivery defaults.

## Why Project Templates Are Needed

Governance work often starts from repeatable project types: metadata inventory, standard mapping confirmation, STG design, quality rule build, and full delivery. Project templates package the correct workflow profile, default review mode, default outputs, and optional domain pack into one reusable preset.

## Domain Pack Versus Workflow Profile

A workflow profile defines which stages run.

A domain pack defines domain-specific defaults and hints used by those stages and their outputs.

## Project Template Versus Workflow Profile

A project template is a project-oriented preset. It points to a base workflow profile and adds default outputs, review mode, and a default domain pack. A workflow profile remains the execution route; the template makes common project starts faster.

## Current Domain Packs

- `customer_domain_pack`
- `transaction_domain_pack`
- `reference_code_domain_pack`
- `supply_chain_finance_domain_pack`

## Current Project Templates

- `metadata_inventory_project`
- `standard_mapping_confirmation_project`
- `stg_structure_design_project`
- `quality_rule_build_project`
- `full_governance_delivery_project`

## Current Boundary

This phase uses local YAML presets and rule-based token matching. It does not perform automatic domain learning, ontology management, external project management integration, LLM calls, embeddings, or vector search.


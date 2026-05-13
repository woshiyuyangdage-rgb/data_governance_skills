# Governance Readiness and Remediation Planning Spec

## Purpose

Governance workflows currently produce diagnosis issues, mapping recommendations, STG suggestions, quality intelligence, confirmed rules, and execution-ready packages. These outputs are useful, but they are still distributed across different sections. Governance readiness scoring turns them into a concise decision view: what is ready, what is partially ready, and what still blocks trustworthy downstream use.

Gap classification explains why an object is not ready. It groups raw signals such as missing descriptions, unmapped fields, low-confidence STG suggestions, quality rule gaps, and review backlog into stable governance gap types.

Remediation planning converts classified gaps into recommended actions. It is not an approval flow or ticketing system. It provides suggested owner roles, priorities, expected outputs, and dependency notes so a local reviewer can decide what to do next.

## Relationship

- `readiness_scores` summarize the current readiness level by table and overall.
- `governance_gaps` explain the missing or risky capabilities behind readiness loss.
- `remediation_actions` describe recommended next actions for the classified gaps.
- `governance_work_package` bundles the scores, gaps, and actions into an exportable local work package.

## Assessment Dimensions

The current rule-based readiness model covers:

- `metadata_readiness`: table and field metadata completion.
- `mapping_readiness`: standard mapping coverage and unmapped fields.
- `stg_readiness`: STG suggestion readiness and low-confidence structural signals.
- `quality_rule_readiness`: quality rule suggestion and confirmed rule coverage.
- `review_completion_readiness`: unresolved manual review and low-confidence review backlog.

## Output Structure

The workflow result may include:

- `readiness_scores`: table-level and overall readiness records.
- `governance_gaps`: aggregated gap records with category, severity, source signals, and suggested owner role.
- `remediation_actions`: action records with priority, owner role, expected output, and dependency notes.
- `governance_work_package`: one bundled package for local export and review.
- `readiness_summary`: compact counts and score distribution.

## Boundary

This layer is rule-based decision support. It does not execute remediation, assign owners, create tickets, update source systems, or call external project management tools. Future integrations can export these work packages into action tracking systems after the local contract stabilizes.

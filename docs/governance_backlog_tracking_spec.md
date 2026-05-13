# Governance Backlog & Tracking Spec

## Purpose

Readiness assessment and remediation planning identify what should be fixed. A governance backlog turns those remediation actions into stable, trackable work items that can be reviewed, filtered, updated, exported, and revisited in later local runs.

The backlog layer answers a practical governance question:

`Which governance actions are open, who should own them, what priority do they have, and what does done mean?`

## Backlog Item And Remediation Action

A `RemediationAction` is a recommended action generated from readiness scores and classified governance gaps. It is advisory and package-oriented.

A `GovernanceBacklogItem` is a trackable local work item derived from a remediation action. It adds:

- deterministic `backlog_id`
- lifecycle `status`
- `owner_role` and priority metadata
- urgency score
- dependency and blocked-by metadata
- completion criteria
- created and updated timestamps
- local notes

The current implementation does not assign real users. It keeps owner role hints so a data governance lead can route work outside the system if needed.

## Status Lifecycle

The first local lifecycle is intentionally small:

- `proposed`: suggested but not yet accepted
- `accepted`: accepted for governance handling
- `in_progress`: governance action is being handled
- `blocked`: action is blocked by a dependency or unresolved issue
- `completed`: action has been completed
- `dropped`: action is intentionally not pursued

Allowed transitions are controlled by `app/config/governance_backlog_policies.yaml`.

## Priority

Backlog priority follows remediation planning:

- `priority_governance`: highest governance urgency
- `key_tracking`: should be tracked as active governance work
- `continuous_observation`: lower urgency or advisory tracking

Priority maps to a lightweight `urgency_score` for dashboard and sorting use.

## Backlog Summary

`BacklogSummary` is a dashboard-ready aggregate with counts by:

- status
- priority
- owner role
- gap type

It also carries blocked and completed counts.

## Current Output Structure

The workflow result can include:

- `governance_backlog_items`
- `backlog_summary`

The local store persists:

- `app/data/governance_backlog/backlog_items.json`
- `app/data/governance_backlog/backlog_snapshots/`

Reports and API outputs expose the same structures for local review and export.

## Boundary

This layer is local, rule-based, and lightweight. It does not:

- connect to Jira, Feishu, DingTalk, TAPD, or other external systems
- auto-assign work to users
- implement approval workflows
- store backlog state in a database
- execute remediation actions

Future extensions can add due dates, SLA policies, project-management adapters, and progress dashboards after the local backlog contract remains stable.


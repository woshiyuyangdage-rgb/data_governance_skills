# Governance Portfolio & Progress Spec

## Purpose

Backlog tracking makes individual remediation actions traceable. Portfolio management adds the next governance layer: it summarizes the backlog across owners, priorities, statuses, gap types, objects, readiness levels, and SLA risk so governance leads can decide where attention is needed.

The portfolio view answers:

`How healthy is the governance backlog as a whole, where is work blocked or overdue, and what progress snapshot can be exported today?`

## Portfolio Summary And Backlog Summary

`BacklogSummary` is a compact backlog aggregate. It focuses on counts by status, priority, owner role, and gap type for the current item set.

`GovernancePortfolioSummary` builds on backlog summary and adds portfolio management signals:

- readiness level distribution
- overdue count
- blocked count
- owner workload
- priority/status/gap summaries that are dashboard-ready

This keeps single-item tracking separate from governance portfolio reporting.

## SLA, Due Date, Aging, And Overdue

The local SLA layer is rule-based and policy-driven:

- `due_date`: the expected handling date inferred from priority and owner role policies
- `age_days`: days since backlog item creation
- `overdue_days`: days past the inferred due date
- `is_overdue`: whether an open item is overdue
- `sla_status`: `on_track`, `warning`, or `overdue`

Completed and dropped items are treated as closed for overdue counting so they do not pollute active SLA risk.

## Progress Snapshot

A `ProgressSnapshot` is a small point-in-time record containing trend-ready fields such as backlog size, completed count, blocked count, overdue count, and average readiness score.

Snapshots are saved locally under:

- `app/data/governance_backlog/progress_snapshots/`

They are not a time-series database. They are auditable local JSON files for lightweight trend export and dashboard preparation.

## Dashboard-Ready Outputs

The workflow result can now include:

- `backlog_sla_statuses`
- `governance_portfolio_summary`
- `progress_snapshot`

Reports, tools, API routes, and Streamlit pages expose these outputs so a governance lead can export them without wiring a BI platform.

## Portfolio Views

The current portfolio layer supports:

- by owner role
- by priority
- by status
- by gap type
- by object type
- overdue and aging analysis
- readiness level distribution
- owner workload

## Boundary

This capability remains local, rule-based, explainable, and single-user. It does not:

- connect to Jira, Feishu, DingTalk, TAPD, BI tools, or external APIs
- send reminders or notifications
- schedule jobs
- create a database-backed warehouse
- implement a full portfolio analytics platform

Future extensions can add KPI dashboards, tuned due-date policies, project-management adapters, and governance portfolio analytics.

"""Review and quality-rule entries for the jobs catalog."""

QUALITY_JOB_ITEMS = [
    {
        "name": "save_mapping_review",
        "method": "POST",
        "path": "/jobs/save-mapping-review",
        "description": "Persist local mapping review records to override storage.",
    },
    {
        "name": "save_stg_review",
        "method": "POST",
        "path": "/jobs/save-stg-review",
        "description": "Persist local STG review records to override storage.",
    },
    {
        "name": "list_review_summary",
        "method": "GET",
        "path": "/jobs/list-review-summary",
        "description": "Return basic counts from locally stored review overrides.",
    },
    {
        "name": "review_quality_rules",
        "method": "POST",
        "path": "/jobs/review-quality-rules",
        "description": "Review suggested quality rules and return confirmed quality rules.",
    },
    {
        "name": "export_confirmed_quality_rules",
        "method": "POST",
        "path": "/jobs/export-confirmed-quality-rules",
        "description": "Export confirmed quality rules as custom JSON or dbt tests YAML.",
    },
    {
        "name": "build_execution_ready_package",
        "method": "POST",
        "path": "/jobs/build-execution-ready-package",
        "description": "Build an execution-ready governance package from confirmed quality rules.",
    },
    {
        "name": "export_execution_ready_package",
        "method": "POST",
        "path": "/jobs/export-execution-ready-package",
        "description": "Export an execution-ready governance package as package JSON, manifest, or dbt YAML.",
    },
]

QUALITY_SUMMARY_JOB_ITEMS = [
    {
        "name": "execution_package_summary",
        "method": "GET",
        "path": "/jobs/execution-package-summary",
        "description": "Return a lightweight summary placeholder for execution package capability.",
    },
    {
        "name": "quality_rule_review_summary",
        "method": "GET",
        "path": "/jobs/quality-rule-review-summary",
        "description": "Return quality rule review counts from stored overrides.",
    },
]

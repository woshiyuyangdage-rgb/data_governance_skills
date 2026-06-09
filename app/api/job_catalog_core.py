"""Core workflow and intent entries for the jobs catalog."""

CORE_JOB_ITEMS = [
    {
        "name": "run_p0_demo",
        "method": "POST",
        "path": "/jobs/run-p0-demo",
        "description": "Run the rule-based P0 pipeline on built-in demo metadata.",
    },
    {
        "name": "run_p0_from_file",
        "method": "POST",
        "path": "/jobs/run-p0-from-file",
        "description": "Run the rule-based P0 pipeline on a local CSV or Excel file path.",
    },
    {
        "name": "learn_metadata_memory_from_file",
        "method": "POST",
        "path": "/jobs/learn-metadata-memory-from-file",
        "description": "Learn local metadata completion memory from a reviewed high-quality metadata file.",
    },
    {
        "name": "save_manual_metadata",
        "method": "POST",
        "path": "/jobs/save-manual-metadata",
        "description": "Save small hand-entered metadata rows as a reusable local CSV file.",
    },
    {
        "name": "run_manual_metadata",
        "method": "POST",
        "path": "/jobs/run-manual-metadata",
        "description": "Save hand-entered metadata rows and run a workflow profile.",
    },
    {
        "name": "run_p0_plus_mapping",
        "method": "POST",
        "path": "/jobs/run-p0-plus-mapping",
        "description": "Run the rule-based P0 pipeline plus P1 standard mapping on a local CSV or Excel file path.",
    },
    {
        "name": "run_p0_plus_mapping_plus_stg",
        "method": "POST",
        "path": "/jobs/run-p0-plus-mapping-plus-stg",
        "description": "Run the rule-based P0 pipeline, P1 standard mapping, and P1.5 STG structure suggestion on a local CSV or Excel file path.",
    },
    {
        "name": "run_p0_plus_mapping_plus_stg_with_review",
        "method": "POST",
        "path": "/jobs/run-p0-plus-mapping-plus-stg-with-review",
        "description": "Run the rule-based P0 pipeline, mapping, and STG suggestion while applying saved local review overrides.",
    },
    {
        "name": "run_p0_plus_mapping_plus_stg_plus_quality",
        "method": "POST",
        "path": "/jobs/run-p0-plus-mapping-plus-stg-plus-quality",
        "description": "Run the rule-based diagnosis, mapping, STG suggestion, and quality rule recommendation workflow on a local CSV or Excel file path.",
    },
    {
        "name": "run_p0_plus_mapping_plus_stg_plus_quality_with_review",
        "method": "POST",
        "path": "/jobs/run-p0-plus-mapping-plus-stg-plus-quality-with-review",
        "description": "Run the rule-based diagnosis, mapping, STG suggestion, and quality rule recommendation workflow while applying saved local review overrides.",
    },
    {
        "name": "run_mapping_only",
        "method": "POST",
        "path": "/jobs/run-mapping-only",
        "description": "Run the rule-based standard mapping workflow on a local CSV or Excel file path.",
    },
    {
        "name": "run_stg_only_from_mapping",
        "method": "POST",
        "path": "/jobs/run-stg-only-from-mapping",
        "description": "Run the rule-based mapping plus STG workflow without full diagnosis packaging.",
    },
    {
        "name": "run_quality_only_from_stg",
        "method": "POST",
        "path": "/jobs/run-quality-only-from-stg",
        "description": "Run the rule-based mapping, STG suggestion, and quality rule recommendation workflow without full diagnosis packaging.",
    },
    {
        "name": "run_quality_only_from_stg_with_review",
        "method": "POST",
        "path": "/jobs/run-quality-only-from-stg-with-review",
        "description": "Run quality rule recommendation with review replay without full diagnosis packaging.",
    },
    {
        "name": "run_governance_task",
        "method": "POST",
        "path": "/jobs/run-governance-task",
        "description": "Run a named workflow profile through the unified governance task router.",
    },
    {
        "name": "list_workflow_profiles",
        "method": "GET",
        "path": "/jobs/list-workflow-profiles",
        "description": "Return enabled workflow profiles for the unified governance router.",
    },
    {
        "name": "interpret_governance_task",
        "method": "POST",
        "path": "/jobs/interpret-governance-task",
        "description": "Interpret natural-language task text into a standard governance task request without executing it.",
    },
    {
        "name": "run_interpreted_governance_task",
        "method": "POST",
        "path": "/jobs/run-interpreted-governance-task",
        "description": "Interpret natural-language task text and then execute it through the unified governance task router.",
    },
]

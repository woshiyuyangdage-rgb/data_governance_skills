# Product Skill Packages

This directory keeps product-level governance skill packages. New internal code should import from these packages instead of the legacy flat wrapper modules.

| Package | Product skill | Responsibility |
| --- | --- | --- |
| `metadata_diagnosis_skill` | `metadata-diagnosis-skill` | Metadata completeness, technical-object detection, naming checks, diagnosis aggregation, and governance task packaging. |
| `data_standard_mapping_skill` | `data-standard-mapping-skill` | Standard-field mapping recommendation and unmapped-field analysis. |
| `stg_standardization_skill` | `stg-standardization-skill` | STG table and field structure recommendation. |
| `data_quality_rule_skill` | `data-quality-rule-skill` | Field-level, cross-field, and domain-aware quality rule recommendation. |
| `dbt_governance_skill` | `dbt-governance-skill` | Placeholder package for execution-ready and dbt-compatible governance artifacts. Current implementation lives under adapters and tools. |
| `governance_report_skill` | `governance-report-skill` | Placeholder package for reporting and delivery outputs. Current implementation lives under reports, delivery, governance, and tools. |

Legacy modules such as `app.core.skills.quality_rule_recommendation` remain as compatibility wrappers. Keep them thin and route new implementation work into the product packages above.

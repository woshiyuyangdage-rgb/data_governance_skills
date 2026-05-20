"""Markdown report analysis section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_mapping_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Standard Mapping Recommendations", ""]
    if result.mapping_summary:
        lines.append(f"- Summary: {result.mapping_summary}")
    if result.mapping_results:
        for mapping_result in result.mapping_results:
            lines.append(
                f"- `{mapping_result.table_name}.{mapping_result.field_name}` -> "
                f"`{mapping_result.recommended_standard_code}` | score={mapping_result.match_score} | "
                f"reason={mapping_result.match_reason}"
            )
    else:
        lines.append("- No standard mapping recommendations generated.")

    lines.extend(["", "# Unmapped or Low-Confidence Fields", ""])
    if result.unmapped_fields:
        for unmapped_field in result.unmapped_fields:
            lines.append(
                f"- `{unmapped_field.table_name}.{unmapped_field.field_name}` | "
                f"best_candidate={unmapped_field.best_candidate_code or 'N/A'} | "
                f"score={unmapped_field.best_candidate_score} | reason={unmapped_field.reason}"
            )
    else:
        lines.append("- No unmapped or low-confidence fields.")

    lines.extend(["", "# Confirmed Mapping Results", ""])
    if result.confirmed_mapping_results:
        for mapping_result in result.confirmed_mapping_results:
            lines.append(
                f"- `{mapping_result.table_name}.{mapping_result.field_name}` -> "
                f"`{mapping_result.recommended_standard_code or 'REJECTED'}` | "
                f"source={mapping_result.confirmed_source or 'review'} | "
                f"action={mapping_result.review_action or 'applied'} | "
                f"note={mapping_result.reviewer_note or 'N/A'}"
            )
    else:
        lines.append("- No confirmed mapping results available.")
    return lines


def build_stg_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# STG Structure Suggestions", ""]
    if result.stg_summary:
        lines.append(f"- Summary: {result.stg_summary}")
    if result.stg_suggestions:
        for table_suggestion in result.stg_suggestions:
            lines.append(
                f"- `{table_suggestion.source_table_name}` -> "
                f"`{table_suggestion.recommended_stg_table_name}` | "
                f"issue_flags={', '.join(table_suggestion.issue_flags) or 'none'}"
            )
        lines.append("")
        lines.append("## STG Field Suggestions")
        lines.append("")
        for field_suggestion in result.stg_field_suggestions:
            lines.append(
                f"- `{field_suggestion.source_table_name}.{field_suggestion.source_field_name}` -> "
                f"`{field_suggestion.recommended_stg_field_name}` | "
                f"type={field_suggestion.recommended_data_type} | "
                f"source={field_suggestion.mapping_source} | action={field_suggestion.action} | "
                f"notes={field_suggestion.notes or 'N/A'}"
            )
    else:
        lines.append("- No STG structure suggestions generated.")

    lines.extend(["", "# Confirmed STG Suggestions", ""])
    if result.confirmed_stg_suggestions:
        for suggestion in result.confirmed_stg_suggestions:
            lines.append(
                f"- `{suggestion.source_table_name}.{suggestion.source_field_name}` -> "
                f"`{suggestion.recommended_stg_field_name}` | "
                f"type={suggestion.recommended_data_type} | "
                f"source={suggestion.confirmed_source or 'review'} | "
                f"action={suggestion.review_action or suggestion.action} | "
                f"note={suggestion.reviewer_note or 'N/A'}"
            )
    else:
        lines.append("- No confirmed STG suggestions available.")
    return lines


def build_quality_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Quality Rule Recommendations", ""]
    if result.quality_rule_summary:
        lines.append(f"- Summary: {result.quality_rule_summary}")
    if result.quality_rule_suggestions:
        for rule in result.quality_rule_suggestions:
            lines.append(
                f"- `{rule.source_table_name}.{rule.source_field_name}` -> "
                f"{rule.rule_type} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"source={rule.recommendation_source} | "
                f"basis={rule.match_basis or 'N/A'} | "
                f"reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No quality rule recommendations generated.")

    lines.extend(["", "# Cross-Field Quality Rules", ""])
    if result.cross_field_quality_rules:
        for rule in result.cross_field_quality_rules:
            lines.append(
                f"- `{rule.source_table_name}` | fields={', '.join(rule.field_group)} | "
                f"{rule.rule_type} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"expression={rule.rule_expression} | reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No cross-field quality rules generated.")

    lines.extend(["", "# Quality Review Queue Summary", ""])
    if result.quality_review_queue_summary:
        for key, value in result.quality_review_queue_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No quality review queue summary available.")

    lines.extend(["", "# Confirmed Quality Rules", ""])
    if result.confirmed_quality_rules:
        for rule in result.confirmed_quality_rules:
            lines.append(
                f"- `{rule.source_table_name}.{rule.source_field_name}` -> "
                f"{rule.rule_type} | scope={rule.rule_scope} | severity={rule.severity} | "
                f"confidence={rule.confidence if rule.confidence is not None else 'N/A'} | "
                f"review_priority={rule.review_priority or 'N/A'} | "
                f"source={rule.confirmation_source} | "
                f"expression={rule.rule_expression or 'N/A'} | "
                f"reason={rule.reason or 'N/A'}"
            )
    else:
        lines.append("- No confirmed quality rules available.")

    lines.extend(["", "# Quality Rule Review Summary", ""])
    if result.quality_rule_review_summary:
        for key, value in result.quality_rule_review_summary.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- No quality rule review summary available.")

    lines.extend(["", "# Rule Export Results", ""])
    if result.rule_export_results:
        for export_result in result.rule_export_results:
            lines.append(
                f"- {export_result.export_format} | status={export_result.status} | "
                f"rules={export_result.rule_count} | path=`{export_result.output_path}`"
            )
    else:
        lines.append("- No rule export results available.")
    return lines


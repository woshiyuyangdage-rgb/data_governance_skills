"""Markdown report intake and review section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_template_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Domain Governance Pack", ""]
    if result.domain_pack_match:
        lines.append(
            f"- Matched pack: `{result.domain_pack_match.matched_pack_name or 'N/A'}`"
        )
        lines.append(f"- Confidence: {result.domain_pack_match.confidence}")
        lines.append(f"- Fallback used: {result.domain_pack_match.fallback_used}")
        lines.append(f"- Matched tokens: {result.domain_pack_match.matched_tokens}")
    else:
        lines.append("- No domain governance pack match attached.")

    lines.extend(["", "# Project Template Applied", ""])
    if result.project_template_result:
        template = result.project_template_result
        lines.append(f"- Template: `{template.template_name}`")
        lines.append(f"- Domain pack: `{template.selected_domain_pack or 'N/A'}`")
        lines.append(f"- Workflow profile: `{template.workflow_profile or 'N/A'}`")
        lines.append(f"- Status: {template.status}")
    else:
        lines.append("- No project template result attached.")

    lines.extend(["", "# Intake Template Diagnosis", ""])
    if result.intake_match_result:
        intake_match = result.intake_match_result
        lines.append(f"- Matched profile: `{intake_match.matched_profile_name or 'N/A'}`")
        lines.append(f"- Confidence: {intake_match.confidence}")
        lines.append(f"- Matched sheet: `{intake_match.matched_sheet_name or 'N/A'}`")
        lines.append(f"- Missing required fields: {intake_match.missing_required_fields}")
    else:
        lines.append("- No intake template diagnosis attached.")

    lines.extend(["", "# Input Normalization Summary", ""])
    if result.intake_normalization_result:
        normalization = result.intake_normalization_result
        lines.append(f"- Profile: `{normalization.profile_name}`")
        lines.append(f"- Rows: {normalization.row_count}")
        lines.append(f"- Tables: {normalization.table_count}")
        lines.append(f"- Status: {normalization.status}")
        if result.intake_mapping_result:
            lines.append(
                f"- Unmapped source columns: {len(result.intake_mapping_result.unmapped_source_columns)}"
            )
    else:
        lines.append("- No intake normalization summary attached.")

    lines.extend(["", "# Confirmation Template Diagnosis", ""])
    if result.confirmation_template_match_result:
        template_match = result.confirmation_template_match_result
        lines.append(
            f"- Matched template: `{template_match.matched_template_name or 'N/A'}`"
        )
        lines.append(f"- Workbook type: `{template_match.workbook_type or 'N/A'}`")
        lines.append(f"- Confidence: {template_match.confidence}")
        lines.append(f"- Matched sheet: `{template_match.matched_sheet_name or 'N/A'}`")
        lines.append(f"- Missing required fields: {template_match.missing_required_fields}")
    else:
        lines.append("- No confirmation template diagnosis attached.")

    lines.extend(["", "# Confirmation Template Mapping Summary", ""])
    if result.confirmation_template_mapping_result:
        template_mapping = result.confirmation_template_mapping_result
        lines.append(f"- Template: `{template_mapping.template_name}`")
        lines.append(f"- Status: {template_mapping.status}")
        lines.append(f"- Mapped fields: {sorted(template_mapping.mapped_fields.keys())}")
        lines.append(
            f"- Unmapped source columns: {template_mapping.unmapped_source_columns}"
        )
    else:
        lines.append("- No confirmation template mapping summary attached.")
    return lines


def build_review_section(result: WorkflowResult) -> list[str]:
    lines = ["", "# Review Summary", ""]
    if result.review_summary:
        lines.append(f"- Accepted: {result.review_summary.accepted_count}")
        lines.append(f"- Rejected: {result.review_summary.rejected_count}")
        lines.append(f"- Edited: {result.review_summary.edited_count}")
        lines.append(f"- Manual Review: {result.review_summary.manual_review_count}")
        lines.append(f"- Total Reviewed: {result.review_summary.total_reviewed_count}")
    else:
        lines.append("- No review summary available.")
    return lines


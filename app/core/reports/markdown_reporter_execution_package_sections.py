"""Markdown report execution package section builders."""

from app.core.models.workflow_result import WorkflowResult


def build_execution_package_sections(result: WorkflowResult) -> list[str]:
    lines = ["", "# Execution-Ready Governance Package", ""]
    if result.execution_ready_package is not None:
        package = result.execution_ready_package
        lines.append(f"- Package ID: `{package.package_id}`")
        lines.append(f"- Package name: `{package.package_name}`")
        lines.append(f"- Rule count: {package.rule_count}")
        if result.execution_package_summary:
            lines.append(
                f"- Field rules: {result.execution_package_summary.get('field_rule_count', 'N/A')}"
            )
            lines.append(
                f"- Cross-field rules: {result.execution_package_summary.get('cross_field_rule_count', 'N/A')}"
            )
            lines.append(
                f"- Non-native rules: {result.execution_package_summary.get('non_native_rule_count', 'N/A')}"
            )
        lines.append(f"- Source profile: {package.source_profile or 'N/A'}")
        lines.append(f"- Summary: {package.summary or 'N/A'}")
        if package.rules:
            lines.append("")
            lines.append("## Execution-Ready Rules")
            lines.append("")
            for rule in package.rules:
                lines.append(
                    f"- `{rule.rule_id}` | `{rule.source_table_name}.{rule.source_field_name}` | "
                    f"{rule.rule_type} | scope={rule.rule_scope} | semantic={rule.semantic_type or 'N/A'} | "
                    f"mode={rule.execution_mode or 'N/A'} | priority={rule.priority or 'N/A'}"
                )
    else:
        lines.append("- No execution-ready package available.")

    lines.extend(["", "# Execution Package Export Results", ""])
    if result.execution_package_export_results:
        for export_result in result.execution_package_export_results:
            lines.append(
                f"- {export_result.export_format} | status={export_result.status} | "
                f"package=`{export_result.package_id}` | rules={export_result.rule_count} | "
                f"path=`{export_result.output_path}`"
            )
    else:
        lines.append("- No execution package export results available.")
    return lines


"""Execution-ready governance package workbench."""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_workflow_result,
    initialize_session_state,
    set_latest_execution_package_export_results,
    set_latest_execution_ready_package,
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.adapters.execution_package_builder import ExecutionPackageBuilder
from app.core.adapters.rule_export_adapter import RuleExportAdapter
from app.core.models.execution_package_export_result import ExecutionPackageExportResult
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file,
)
from app.ui.page_overview import build_workflow_overview
from app.ui.performance_helpers import render_lazy_dataframe_section
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_metric_row, render_page_header
from app.ui.workbench_cache import (
    execution_package_export_results_to_dataframe,
    execution_package_summary_to_dataframe,
    execution_ready_rules_to_dataframe,
)

EXPORT_FORMAT_LABELS = {
    "package JSON": "执行包 JSON",
    "package manifest": "执行包清单",
    "dbt YAML": "dbt YAML",
}

initialize_session_state()

render_page_header(
    "执行准备包",
    (
        "基于已确认质量规则构建执行准备包，并导出给后续执行引擎适配器使用的资产。"
    ),
)

result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()

if result is None:
    st.warning("当前还没有工作流结果，请先运行质量规则工作流。")
else:
    render_result_overview(
        build_workflow_overview(
            result,
            title="执行包总览",
            next_step="先确认质量规则，再构建或导出执行包。",
        )
    )

    confirmed_rules = result.confirmed_quality_rules
    package = result.execution_ready_package

    summary = result.execution_package_summary or {}
    render_metric_row(
        [
            ("已确认规则", len(confirmed_rules)),
            ("包内规则", package.rule_count if package else 0),
            ("字段规则", int(summary.get("field_rule_count", 0) or 0)),
            ("跨字段规则", int(summary.get("cross_field_rule_count", 0) or 0)),
            ("非原生规则", int(summary.get("non_native_rule_count", 0) or 0)),
            ("导出数", len(result.execution_package_export_results)),
        ],
        max_columns=6,
    )

    col_build, col_rerun = st.columns(2)
    with col_build:
        if st.button("构建执行准备包", type="primary"):
            if not confirmed_rules:
                st.warning("暂无可打包的已确认质量规则。")
            else:
                builder = ExecutionPackageBuilder()
                package = builder.build_package(
                    confirmed_rules,
                    profile_name="streamlit_execution_package",
                    trace_metadata={"source": "streamlit"},
                )
                result.execution_ready_package = package
                result.execution_package_summary = builder.summarize_package(package)
                set_workflow_result_state(result)
                set_latest_execution_ready_package(package)
                st.success("执行准备包已构建。")

    with col_rerun:
        if st.button("重新评审并构建执行包"):
            if not uploaded_file_path:
                st.warning("当前没有输入文件路径，请先运行基于文件的工作流。")
            else:
                try:
                    with st.spinner("正在回放质量评审并构建执行包..."):
                        rerun_result = (
                            run_p0_plus_mapping_plus_stg_plus_quality_with_review_and_package_from_file(
                                uploaded_file_path
                            )
                        )
                except Exception as exc:
                    st.error(f"重新运行执行包工作流失败: {exc}")
                else:
                    set_workflow_result_state(rerun_result, file_path=uploaded_file_path)
                    result = rerun_result
                    package = rerun_result.execution_ready_package
                    st.success("质量评审回放和执行包构建已完成。")

    st.subheader("执行包汇总")
    summary_df = execution_package_summary_to_dataframe(
        result.execution_ready_package,
        result.execution_package_summary,
    )
    if not summary_df.empty:
        render_lazy_dataframe_section(
            "执行包汇总",
            summary_df,
            compact=True,
            key_prefix="execution_package_summary",
        )
    else:
        st.info("暂无执行包汇总。")

    st.subheader("执行准备规则")
    rules_df = execution_ready_rules_to_dataframe(result.execution_ready_package)
    if not rules_df.empty:
        render_lazy_dataframe_section(
            "执行准备规则",
            rules_df,
            compact=True,
            key_prefix="execution_ready_rules",
        )
    else:
        st.info("暂无执行准备规则。")

    st.subheader("导出执行包")
    export_format = st.selectbox(
        "导出格式",
        options=["package JSON", "package manifest", "dbt YAML"],
        format_func=lambda value: EXPORT_FORMAT_LABELS.get(value, value),
    )
    if st.button("导出执行准备包"):
        current_result: WorkflowResult | None = get_workflow_result()
        if current_result is None:
            st.warning("当前没有可导出的工作流结果。")
            st.stop()
        current_package = current_result.execution_ready_package
        if current_package is None:
            st.warning("请先构建执行准备包再导出。")
        else:
            adapter = RuleExportAdapter()
            output_dir = PROJECT_ROOT / "outputs" / "execution_packages"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            try:
                if export_format == "package JSON":
                    export_result = adapter.export_execution_ready_package_json(
                        current_package,
                        str(output_dir / f"execution_ready_package_{timestamp}.json"),
                    )
                elif export_format == "package manifest":
                    export_result = adapter.export_execution_ready_package_manifest(
                        current_package,
                        str(
                            output_dir
                            / f"execution_ready_package_{timestamp}_manifest.json"
                        ),
                    )
                else:
                    dbt_result = adapter.export_dbt_tests_yaml(
                        current_package,
                        str(output_dir / f"execution_ready_package_{timestamp}_dbt.yml"),
                    )
                    export_result = ExecutionPackageExportResult(
                        export_format=dbt_result.export_format,
                        output_path=dbt_result.output_path,
                        package_id=current_package.package_id,
                        rule_count=dbt_result.rule_count,
                        status=dbt_result.status,
                        message=dbt_result.message,
                    )
                current_result.execution_package_export_results.append(export_result)
                set_workflow_result_state(current_result)
                set_latest_execution_package_export_results(
                    current_result.execution_package_export_results
                )
                st.success("执行准备包已导出。")
            except Exception as exc:
                st.error(f"导出执行准备包失败: {exc}")

    st.subheader("执行包导出结果")
    export_df = execution_package_export_results_to_dataframe(
        result.execution_package_export_results
    )
    if not export_df.empty:
        render_lazy_dataframe_section(
            "执行包导出结果",
            export_df,
            compact=True,
            key_prefix="execution_package_exports",
        )
    else:
        st.info("暂无执行包导出结果。")

"""Governance readiness and remediation workbench."""

import json
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
    set_workflow_result_state,
)

ensure_project_root_on_path()

from app.core.governance import (
    AiReadyAssessor,
    GapClassifier,
    ReadinessAssessor,
    RemediationPlanner,
)
from app.core.models.workflow_result import WorkflowResult
from app.core.orchestrator.pipeline_service import (
    run_full_governance_work_package_from_file,
)
from app.ui.page_overview import build_workflow_overview
from app.ui.performance_helpers import (
    render_dataframe_multiselect_filter,
    render_lazy_dataframe_section,
)
from app.ui.result_overview import render_result_overview
from app.ui.status_blocks import render_metric_row, render_page_header
from app.ui.workbench_cache import (
    ai_ready_scores_to_dataframe,
    governance_gaps_to_dataframe,
    governance_work_package_summary_to_dataframe,
    readiness_scores_to_dataframe,
    remediation_actions_to_dataframe,
)

initialize_session_state()

render_page_header(
    "治理就绪度",
    "评估治理就绪度，分类治理缺口，并构建整改工作包。",
)


def _build_readiness_from_result(result: WorkflowResult) -> WorkflowResult:
    assessor = ReadinessAssessor()
    ai_ready_assessor = AiReadyAssessor()
    classifier = GapClassifier()
    planner = RemediationPlanner()
    result.readiness_scores = assessor.assess(result)
    result.ai_ready_scores = ai_ready_assessor.assess(result)
    result.ai_ready_summary = ai_ready_assessor.summarize(result.ai_ready_scores)
    result.governance_gaps = classifier.classify(result)
    result.remediation_actions = planner.build_actions(
        result.readiness_scores,
        result.governance_gaps,
    )
    result.governance_work_package = planner.build_work_package(
        result.readiness_scores,
        result.governance_gaps,
        result.remediation_actions,
        package_name="streamlit_governance_work_package",
    )
    result.readiness_summary = planner.summarize(
        result.readiness_scores,
        result.governance_gaps,
        result.remediation_actions,
    )
    return result


result: WorkflowResult | None = get_workflow_result()
uploaded_file_path = get_current_input_file_path()

col_run, col_export = st.columns(2)
with col_run:
    if st.button("运行就绪度评估", type="primary"):
        if uploaded_file_path:
            try:
                with st.spinner("正在运行完整治理工作包流程..."):
                    result = run_full_governance_work_package_from_file(uploaded_file_path)
            except Exception as exc:
                st.error(f"运行就绪度评估失败: {exc}")
            else:
                set_workflow_result_state(result, file_path=uploaded_file_path)
                st.success("治理就绪度评估完成。")
        elif result is not None:
            result = _build_readiness_from_result(result)
            set_workflow_result_state(result)
            st.success("已基于当前结果完成治理就绪度评估。")
        else:
            st.warning("请先运行工作流或上传元数据文件。")

with col_export:
    if st.button("导出治理工作包"):
        current_result: WorkflowResult | None = get_workflow_result()
        if current_result is None or current_result.governance_work_package is None:
            st.warning("请先构建治理工作包再导出。")
        else:
            output_dir = PROJECT_ROOT / "outputs" / "governance_work_packages"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"governance_work_package_{timestamp}.json"
            output_path.write_text(
                json.dumps(
                    current_result.governance_work_package.model_dump(),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            st.success(f"治理工作包已导出到 {output_path}")

result = get_workflow_result()
if result is None:
    st.info("当前还没有工作流结果。")
else:
    render_result_overview(
        build_workflow_overview(
            result,
            title="治理就绪总览",
            next_step="先确认缺口和整改动作，再导出工作包。",
        )
    )

    render_metric_row(
        [
            ("就绪度评分", len(result.readiness_scores)),
            ("AI-ready 评分", len(result.ai_ready_scores)),
            ("治理缺口", len(result.governance_gaps)),
            ("整改动作", len(result.remediation_actions)),
            (
                "工作包",
                result.governance_work_package.package_name
                if result.governance_work_package is not None
                else "未构建",
            ),
        ],
    )

    st.subheader("工作包汇总")
    summary_df = governance_work_package_summary_to_dataframe(
        result.governance_work_package,
        result.readiness_summary,
    )
    if not summary_df.empty:
        render_lazy_dataframe_section(
            "工作包汇总",
            summary_df,
            compact=True,
            key_prefix="readiness_work_package_summary",
        )
    else:
        st.info("暂无工作包汇总。")

    st.subheader("表级就绪度")
    readiness_df = readiness_scores_to_dataframe(result.readiness_scores)
    readiness_df = render_dataframe_multiselect_filter(
        readiness_df,
        "readiness_level",
        "筛选就绪等级",
    )
    if not readiness_df.empty:
        render_lazy_dataframe_section(
            "表级就绪度",
            readiness_df,
            compact=True,
            key_prefix="readiness_scores",
        )
    else:
        st.info("暂无就绪度评分。")

    st.subheader("AI-ready 评估")
    ai_ready_df = ai_ready_scores_to_dataframe(result.ai_ready_scores)
    ai_ready_df = render_dataframe_multiselect_filter(
        ai_ready_df,
        "ai_ready_level",
        "筛选 AI-ready 等级",
    )
    if not ai_ready_df.empty:
        render_lazy_dataframe_section(
            "AI-ready 评估",
            ai_ready_df,
            compact=True,
            key_prefix="ai_ready_scores",
        )
    else:
        st.info("暂无 AI-ready 评分。")

    st.subheader("治理缺口")
    gaps_df = governance_gaps_to_dataframe(result.governance_gaps)
    gaps_df = render_dataframe_multiselect_filter(gaps_df, "gap_type", "筛选缺口类型")
    if not gaps_df.empty:
        render_lazy_dataframe_section(
            "治理缺口",
            gaps_df,
            compact=True,
            key_prefix="readiness_gaps",
        )
    else:
        st.info("暂无治理缺口。")

    st.subheader("整改动作")
    actions_df = remediation_actions_to_dataframe(result.remediation_actions)
    actions_df = render_dataframe_multiselect_filter(
        actions_df,
        "owner_role",
        "筛选责任角色",
    )
    actions_df = render_dataframe_multiselect_filter(
        actions_df,
        "priority",
        "筛选优先级",
    )
    if not actions_df.empty:
        render_lazy_dataframe_section(
            "整改动作",
            actions_df,
            compact=True,
            key_prefix="readiness_actions",
        )
    else:
        st.info("暂无整改动作。")

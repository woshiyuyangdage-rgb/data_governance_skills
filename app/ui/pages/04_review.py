"""Review page for saving local overrides and rerunning with review memory."""

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.explanation_blocks import render_explanation_block
from app.ui.page_overview import build_workflow_overview
from app.ui.page_utils import (
    ensure_project_root_on_path,
    get_current_input_file_path,
    get_latest_review_summary,
    get_session_value,
    get_uploaded_file_signature,
    get_workflow_result,
    initialize_session_state,
    set_latest_review_summary,
    set_workflow_result_state,
)
from app.ui.performance_helpers import render_lazy_dataframe_section
from app.ui.result_overview import render_result_overview
from app.ui.review_form_helpers import (
    candidate_evidence,
    collect_mapping_review_inputs,
    collect_stg_review_inputs,
)
from app.ui.status_blocks import render_page_header

ensure_project_root_on_path()

from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_with_review_from_file,
    run_p0_plus_mapping_with_review_from_file,
)
from app.core.review.override_store import (
    build_mapping_override_lookup,
    build_stg_override_lookup,
    save_mapping_review_records,
    save_stg_review_records,
)
from app.core.review.review_service import (
    build_mapping_review_records_from_results,
    build_stg_review_records_from_results,
    summarize_review_records,
)
from app.ui.workbench_cache import (
    clear_review_override_caches,
    load_mapping_overrides_cached,
    load_stg_overrides_cached,
    review_summary_to_dataframe,
)

initialize_session_state()

render_page_header(
    "人工评审工作台",
    "确认、拒绝、编辑或标记建议，并把覆盖结果写回本地。",
)

result = get_workflow_result()
uploaded_file_path = get_current_input_file_path(prefer_workflow_result=True)

if result is None:
    st.warning("当前还没有工作流结果，请先运行诊断。")
else:
    mapping_results = result.mapping_results
    stg_suggestions = result.stg_field_suggestions
    mapping_overrides = load_mapping_overrides_cached(
        get_uploaded_file_signature()
    )
    stg_overrides = load_stg_overrides_cached(
        get_uploaded_file_signature()
    )
    mapping_override_lookup = build_mapping_override_lookup(mapping_overrides)
    stg_override_lookup = build_stg_override_lookup(stg_overrides)

    render_result_overview(
        build_workflow_overview(
            result,
            title="评审总览",
            next_step="保存后可以在本页重新运行，验证覆盖是否生效。",
        )
    )

    if not mapping_results and not stg_suggestions:
        st.warning("当前结果没有可评审的映射或 STG 建议。")
    else:
        review_actions = ["accept", "reject", "edit", "mark_for_manual_review"]

        with st.form("review_records_form"):
            st.subheader("映射评审")
            if mapping_results:
                for mapping_result in mapping_results:
                    key = f"{mapping_result.table_name}.{mapping_result.field_name}"
                    existing_override = mapping_override_lookup.get(key)
                    with st.expander(f"映射: {key}", expanded=False):
                        render_explanation_block(
                            "推荐说明",
                            summary=mapping_result.match_reason or "暂无匹配原因。",
                            details=[
                                ("建议标准", mapping_result.recommended_standard_code or "N/A"),
                                ("标准名称", mapping_result.recommended_standard_name or "N/A"),
                                ("标准中文名", mapping_result.recommended_standard_name_cn or "N/A"),
                                ("命中分数", mapping_result.match_score),
                                ("候选数", mapping_result.candidate_count),
                            ],
                            evidence=candidate_evidence(mapping_result.top_candidates),
                            next_step="确认后再保存该条覆盖。",
                        )
                        if existing_override is not None:
                            st.info(
                                "已保存覆盖: "
                                f"`{existing_override.review_action}` -> "
                                f"`{existing_override.final_standard_code or 'N/A'}`"
                            )
                        st.selectbox(
                            "评审动作",
                            review_actions,
                            index=review_actions.index(
                                existing_override.review_action
                                if existing_override is not None
                                and existing_override.review_action in review_actions
                                else "accept"
                            ),
                            key=f"mapping_action_{key}",
                        )
                        st.text_input(
                            "最终标准编码",
                            value=(
                                existing_override.final_standard_code
                                if existing_override is not None
                                else mapping_result.recommended_standard_code or ""
                            ),
                            key=f"mapping_final_{key}",
                        )
                        st.text_area(
                            "评审备注",
                            value=(
                                existing_override.reviewer_note
                                if existing_override is not None
                                and existing_override.reviewer_note is not None
                                else ""
                            ),
                            key=f"mapping_note_{key}",
                            height=80,
                        )
            else:
                st.info("暂无可评审的映射建议。")

            st.subheader("STG 评审")
            if stg_suggestions:
                for suggestion in stg_suggestions:
                    key = f"{suggestion.source_table_name}.{suggestion.source_field_name}"
                    existing_override = stg_override_lookup.get(key)
                    with st.expander(f"STG: {key}", expanded=False):
                        render_explanation_block(
                            "推荐说明",
                            summary=suggestion.notes or "暂无建议说明。",
                            details=[
                                ("建议字段", suggestion.recommended_stg_field_name),
                                ("建议中文名", suggestion.recommended_stg_field_name_cn or "N/A"),
                                ("建议类型", suggestion.recommended_data_type or "N/A"),
                                ("映射来源", suggestion.mapping_source),
                                ("命中分数", suggestion.match_score),
                                ("动作", suggestion.action),
                                ("可空", suggestion.nullable),
                            ],
                            evidence=[
                                f"source_table={suggestion.source_table_name}",
                                f"source_field={suggestion.source_field_name}",
                            ],
                            next_step="确认后再保存该条覆盖。",
                        )
                        if existing_override is not None:
                            st.info(
                                "已保存覆盖: "
                                f"`{existing_override.review_action}` -> "
                                f"`{existing_override.final_stg_field_name or 'N/A'}` / "
                                f"`{existing_override.final_data_type or 'N/A'}`"
                            )
                        st.selectbox(
                            "评审动作",
                            review_actions,
                            index=review_actions.index(
                                existing_override.review_action
                                if existing_override is not None
                                and existing_override.review_action in review_actions
                                else "accept"
                            ),
                            key=f"stg_action_{key}",
                        )
                        st.text_input(
                            "最终 STG 字段名",
                            value=(
                                existing_override.final_stg_field_name
                                if existing_override is not None
                                and existing_override.final_stg_field_name is not None
                                else suggestion.recommended_stg_field_name
                            ),
                            key=f"stg_final_name_{key}",
                        )
                        st.text_input(
                            "最终数据类型",
                            value=(
                                existing_override.final_data_type
                                if existing_override is not None
                                and existing_override.final_data_type is not None
                                else suggestion.recommended_data_type or ""
                            ),
                            key=f"stg_final_type_{key}",
                        )
                        st.text_area(
                            "评审备注",
                            value=(
                                existing_override.reviewer_note
                                if existing_override is not None
                                and existing_override.reviewer_note is not None
                                else ""
                            ),
                            key=f"stg_note_{key}",
                            height=80,
                        )
            else:
                st.info("暂无可评审的 STG 建议。")

            save_clicked = st.form_submit_button("保存评审记录", type="primary")

        if save_clicked:
            mapping_inputs = collect_mapping_review_inputs(
                mapping_results,
                get_session_value,
            )
            stg_inputs = collect_stg_review_inputs(
                stg_suggestions,
                get_session_value,
            )

            mapping_records = build_mapping_review_records_from_results(
                mapping_results,
                mapping_inputs,
                source="streamlit_review",
            )
            stg_records = build_stg_review_records_from_results(
                stg_suggestions,
                stg_inputs,
                source="streamlit_review",
            )

            try:
                if mapping_records:
                    save_mapping_review_records(mapping_records)
                if stg_records:
                    save_stg_review_records(stg_records)
                clear_review_override_caches()
            except Exception as exc:
                st.error(f"保存评审记录失败: {exc}")
            else:
                review_summary = summarize_review_records(mapping_records, stg_records)
                set_latest_review_summary(review_summary)
                st.success("评审记录已保存到本地覆盖存储。")

        st.subheader("已保存评审汇总")
        stored_review_summary = summarize_review_records(
            mapping_overrides,
            stg_overrides,
        )
        stored_summary_df = review_summary_to_dataframe(stored_review_summary)
        render_lazy_dataframe_section(
            "已保存评审汇总",
            stored_summary_df,
            empty_message="暂无已保存评审汇总。",
            compact=True,
            key_prefix="stored_review_summary",
        )

        if st.button("带覆盖重新运行"):
            if not uploaded_file_path:
                st.warning("当前没有输入文件路径，请先重新运行诊断。")
            else:
                try:
                    with st.spinner("正在带本地覆盖重新运行工作流..."):
                        if result.stg_field_suggestions or result.stg_suggestions:
                            rerun_result = run_p0_plus_mapping_plus_stg_with_review_from_file(
                                uploaded_file_path
                            )
                        else:
                            rerun_result = run_p0_plus_mapping_with_review_from_file(
                                uploaded_file_path
                            )
                except Exception as exc:
                    st.error(f"带覆盖重新运行失败: {exc}")
                else:
                    set_workflow_result_state(rerun_result, file_path=uploaded_file_path)
                    set_latest_review_summary(rerun_result.review_summary)
                    st.success("工作流已应用保存的覆盖并重新运行。")

        latest_review_summary = get_latest_review_summary()
        if latest_review_summary is not None:
            st.subheader("最近评审汇总")
            latest_summary_df = review_summary_to_dataframe(latest_review_summary)
            render_lazy_dataframe_section(
                "最近评审汇总",
                latest_summary_df,
                empty_message="暂无最近评审汇总。",
                compact=True,
                key_prefix="latest_review_summary",
            )

"""Review page for saving local overrides and rerunning with review memory."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state
from app.ui.explanation_blocks import render_explanation_block
from app.ui.performance_helpers import render_lazy_dataframe_section

ensure_project_root_on_path()

from app.core.orchestrator.pipeline_service import (
    run_p0_plus_mapping_plus_stg_with_review_from_file,
    run_p0_plus_mapping_with_review_from_file,
)
from app.core.review.override_store import (
    build_mapping_override_lookup,
    build_stg_override_lookup,
    load_mapping_overrides,
    load_stg_overrides,
)
from app.core.review.review_service import (
    build_mapping_review_records_from_results,
    build_stg_review_records_from_results,
    summarize_review_records,
)
from app.core.review.override_store import save_mapping_review_records, save_stg_review_records
from app.ui.workbench_cache import (
    clear_review_override_caches,
    load_mapping_overrides_cached,
    load_stg_overrides_cached,
    review_summary_to_dataframe,
)

initialize_session_state()

st.title("Review Workbench")
st.write("确认、拒绝、编辑或标记建议，并把覆盖结果写回本地。")
st.caption("Quality rule review and rule export are available in the Quality Rules page.")

result = st.session_state.get("workflow_result")
uploaded_file_path = st.session_state.get("workflow_result_file_path")

if result is None:
    st.warning("No workflow result is available yet. Please run diagnosis first.")
else:
    mapping_results = result.mapping_results
    stg_suggestions = result.stg_field_suggestions
    mapping_overrides = load_mapping_overrides_cached(
        st.session_state.get("uploaded_file_signature")
    )
    stg_overrides = load_stg_overrides_cached(
        st.session_state.get("uploaded_file_signature")
    )
    mapping_override_lookup = build_mapping_override_lookup(mapping_overrides)
    stg_override_lookup = build_stg_override_lookup(stg_overrides)

    render_explanation_block(
        "评审概览",
        summary="先看当前建议，再决定是否保存本地覆盖。",
        details=[
            ("输入文件", uploaded_file_path or "N/A"),
            ("映射建议", len(mapping_results)),
            ("STG 建议", len(stg_suggestions)),
            ("已有映射覆盖", len(mapping_overrides)),
            ("已有 STG 覆盖", len(stg_overrides)),
        ],
        next_step="保存后可以在本页重新运行，验证覆盖是否生效。",
    )

    if not mapping_results and not stg_suggestions:
        st.warning("Current result does not include mapping or STG suggestions to review.")
    else:
        review_actions = ["accept", "reject", "edit", "mark_for_manual_review"]

        def _candidate_evidence(top_candidates: list[dict[str, object]]) -> list[str]:
            evidence: list[str] = []
            for candidate in top_candidates:
                standard_code = candidate.get("standard_code") or "N/A"
                standard_name = candidate.get("standard_name") or "N/A"
                match_score = candidate.get("match_score")
                match_reason = candidate.get("match_reason") or "N/A"
                evidence.append(
                    f"{standard_code} | {standard_name} | score={match_score} | {match_reason}"
                )
            return evidence

        with st.form("review_records_form"):
            st.subheader("Mapping Review")
            if mapping_results:
                for mapping_result in mapping_results:
                    key = f"{mapping_result.table_name}.{mapping_result.field_name}"
                    existing_override = mapping_override_lookup.get(key)
                    with st.expander(f"Mapping: {key}", expanded=False):
                        render_explanation_block(
                            "推荐说明",
                            summary=mapping_result.match_reason or "No match reason available.",
                            details=[
                                ("建议标准", mapping_result.recommended_standard_code or "N/A"),
                                ("标准名称", mapping_result.recommended_standard_name or "N/A"),
                                ("标准中文名", mapping_result.recommended_standard_name_cn or "N/A"),
                                ("命中分数", mapping_result.match_score),
                                ("候选数", mapping_result.candidate_count),
                            ],
                            evidence=_candidate_evidence(mapping_result.top_candidates),
                            next_step="确认后再保存该条覆盖。",
                        )
                        if existing_override is not None:
                            st.info(
                                "Saved override: "
                                f"`{existing_override.review_action}` -> "
                                f"`{existing_override.final_standard_code or 'N/A'}`"
                            )
                        st.selectbox(
                            "Review action",
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
                            "Final standard code",
                            value=(
                                existing_override.final_standard_code
                                if existing_override is not None
                                else mapping_result.recommended_standard_code or ""
                            ),
                            key=f"mapping_final_{key}",
                        )
                        st.text_area(
                            "Reviewer note",
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
                st.info("No mapping suggestions are available to review.")

            st.subheader("STG Review")
            if stg_suggestions:
                for suggestion in stg_suggestions:
                    key = f"{suggestion.source_table_name}.{suggestion.source_field_name}"
                    existing_override = stg_override_lookup.get(key)
                    with st.expander(f"STG: {key}", expanded=False):
                        render_explanation_block(
                            "推荐说明",
                            summary=suggestion.notes or "No suggestion note available.",
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
                                "Saved override: "
                                f"`{existing_override.review_action}` -> "
                                f"`{existing_override.final_stg_field_name or 'N/A'}` / "
                                f"`{existing_override.final_data_type or 'N/A'}`"
                            )
                        st.selectbox(
                            "Review action",
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
                            "Final STG field name",
                            value=(
                                existing_override.final_stg_field_name
                                if existing_override is not None
                                and existing_override.final_stg_field_name is not None
                                else suggestion.recommended_stg_field_name
                            ),
                            key=f"stg_final_name_{key}",
                        )
                        st.text_input(
                            "Final data type",
                            value=(
                                existing_override.final_data_type
                                if existing_override is not None
                                and existing_override.final_data_type is not None
                                else suggestion.recommended_data_type or ""
                            ),
                            key=f"stg_final_type_{key}",
                        )
                        st.text_area(
                            "Reviewer note",
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
                st.info("No STG suggestions are available to review.")

            save_clicked = st.form_submit_button("Save Review Records", type="primary")

        if save_clicked:
            mapping_inputs = {
                f"{item.table_name}.{item.field_name}": {
                    "review_action": st.session_state.get(
                        f"mapping_action_{item.table_name}.{item.field_name}"
                    ),
                    "final_standard_code": st.session_state.get(
                        f"mapping_final_{item.table_name}.{item.field_name}"
                    ),
                    "reviewer_note": st.session_state.get(
                        f"mapping_note_{item.table_name}.{item.field_name}"
                    ),
                }
                for item in mapping_results
            }
            stg_inputs = {
                f"{item.source_table_name}.{item.source_field_name}": {
                    "review_action": st.session_state.get(
                        f"stg_action_{item.source_table_name}.{item.source_field_name}"
                    ),
                    "final_stg_field_name": st.session_state.get(
                        f"stg_final_name_{item.source_table_name}.{item.source_field_name}"
                    ),
                    "final_data_type": st.session_state.get(
                        f"stg_final_type_{item.source_table_name}.{item.source_field_name}"
                    ),
                    "reviewer_note": st.session_state.get(
                        f"stg_note_{item.source_table_name}.{item.source_field_name}"
                    ),
                }
                for item in stg_suggestions
            }

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
                st.error(f"Failed to save review records: {exc}")
            else:
                review_summary = summarize_review_records(mapping_records, stg_records)
                st.session_state["latest_review_summary"] = review_summary
                st.success("Review records were saved to local override storage.")

        st.subheader("Stored Review Summary")
        stored_review_summary = summarize_review_records(
            mapping_overrides,
            stg_overrides,
        )
        stored_summary_df = review_summary_to_dataframe(stored_review_summary)
        render_lazy_dataframe_section(
            "Stored Review Summary",
            stored_summary_df,
            empty_message="No stored review summary is available.",
            compact=True,
            key_prefix="stored_review_summary",
        )

        if st.button("Re-run With Overrides"):
            if not uploaded_file_path:
                st.warning("No input file path is available. Please run diagnosis again first.")
            else:
                try:
                    with st.spinner("Re-running workflow with local overrides..."):
                        if result.stg_field_suggestions or result.stg_suggestions:
                            rerun_result = run_p0_plus_mapping_plus_stg_with_review_from_file(
                                uploaded_file_path
                            )
                        else:
                            rerun_result = run_p0_plus_mapping_with_review_from_file(
                                uploaded_file_path
                            )
                except Exception as exc:
                    st.error(f"Failed to rerun with overrides: {exc}")
                else:
                    st.session_state["workflow_result"] = rerun_result
                    st.session_state["workflow_result_file_path"] = uploaded_file_path
                    st.session_state["latest_review_summary"] = rerun_result.review_summary
                    st.success("Workflow re-ran with saved overrides applied.")

        latest_review_summary = st.session_state.get("latest_review_summary")
        if latest_review_summary is not None:
            st.subheader("Latest Review Summary")
            latest_summary_df = review_summary_to_dataframe(latest_review_summary)
            render_lazy_dataframe_section(
                "Latest Review Summary",
                latest_summary_df,
                empty_message="No latest review summary is available.",
                compact=True,
                key_prefix="latest_review_summary",
            )

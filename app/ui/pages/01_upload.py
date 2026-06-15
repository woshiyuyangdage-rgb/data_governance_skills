"""Upload page for local metadata files."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    UPLOAD_OUTPUT_DIR,
    ensure_agent_shell_session_id,
    ensure_project_root_on_path,
    get_uploaded_file_extension,
    get_uploaded_file_name,
    get_uploaded_file_path,
    get_uploaded_file_signature,
    get_uploaded_file_size,
    initialize_session_state,
    set_uploaded_file_state,
)
from app.ui.manual_metadata_editor import (
    MANUAL_METADATA_DELETE_COLUMN,
    append_manual_metadata_row,
    apply_manual_metadata_editor_changes,
    delete_selected_manual_metadata_rows,
    editor_dataframe_to_manual_records,
    ensure_manual_metadata_rows,
    manual_metadata_editor_version,
    manual_metadata_rows_to_editor_dataframe,
    reset_manual_metadata_rows,
)
from app.ui.performance_helpers import ensure_large_file_runtime_ready
from app.ui.status_blocks import render_metric_row, render_page_header
from app.ui.workbench_cache import (
    content_signature,
)
from app.ui.workflow_run_panel import render_workflow_run_panel

ensure_project_root_on_path()

from app.core.agent.session_store import (
    set_last_uploaded_file,
)
from app.core.parser.metadata_completion import (
    apply_reviewed_completion_values,
    complete_metadata_file,
    metadata_completion_changes_to_dataframe,
    save_completed_metadata,
)
from app.core.parser.metadata_learning import (
    learn_metadata_memory_from_dataframe,
    learn_metadata_memory_from_file,
)
from app.core.parser.manual_metadata_input import save_manual_metadata_records
from app.core.utils.file_utils import get_file_extension, save_uploaded_file

initialize_session_state()

render_page_header(
    "上传元数据",
    "上传符合模板的本地 CSV 或 Excel 文件，或手工录入少量元数据，作为后续诊断与评审的输入。",
)

st.subheader("模板说明")
st.caption(f"详细说明: {INPUT_TEMPLATE_DOC_PATH}")
st.markdown(
    """
    - 支持格式: `csv`, `xlsx`
    - 推荐粒度: `table + field-level`
    - 必填列: `table_name`
    - 推荐字段列: `field_name`
    """
)

uploaded_file = st.file_uploader(
    "选择元数据文件",
    type=["csv", "xlsx"],
    help="上传后会本地保存，并进入诊断流程。",
)

if uploaded_file is not None:
    current_signature = content_signature(uploaded_file.getvalue())
    saved_path = get_uploaded_file_path()
    should_save = (
        current_signature != get_uploaded_file_signature()
        or not saved_path
        or not Path(saved_path).exists()
    )

    if should_save:
        try:
            saved_path = save_uploaded_file(uploaded_file, UPLOAD_OUTPUT_DIR)
        except Exception as exc:
            st.error(f"保存上传文件失败: {exc}")
        else:
            set_uploaded_file_state(
                file_path=saved_path,
                file_name=uploaded_file.name,
                file_size=uploaded_file.size,
                file_extension=get_file_extension(uploaded_file.name),
                file_signature=current_signature,
            )
            st.success("文件已保存到本地。")
            ensure_large_file_runtime_ready(saved_path, current_signature)
    else:
        ensure_large_file_runtime_ready(saved_path, current_signature)

st.subheader("手工录入元数据")
st.caption(
    "适合少量表字段。可以直接修改表格，勾选删除列后点击删除选中行；"
    "保存后会生成本地 CSV 并作为当前输入文件使用。"
)

manual_rows = ensure_manual_metadata_rows(st.session_state)
manual_editor_df = manual_metadata_rows_to_editor_dataframe(manual_rows)
manual_df = st.data_editor(
    manual_editor_df,
    num_rows="dynamic",
    use_container_width=True,
    key=f"manual_metadata_editor_{manual_metadata_editor_version(st.session_state)}",
    column_config={
        MANUAL_METADATA_DELETE_COLUMN: st.column_config.CheckboxColumn(
            "删除",
            help="勾选后点击“删除选中行”。",
            default=False,
        )
    },
)

action_col1, action_col2, action_col3, action_col4 = st.columns(4)
with action_col1:
    if st.button("新增空行", use_container_width=True):
        apply_manual_metadata_editor_changes(st.session_state, manual_df)
        append_manual_metadata_row(st.session_state)
        st.rerun()
with action_col2:
    if st.button("应用修改", use_container_width=True):
        apply_manual_metadata_editor_changes(st.session_state, manual_df)
        st.success("表格修改已应用。")
with action_col3:
    if st.button("删除选中行", use_container_width=True):
        deleted_count = delete_selected_manual_metadata_rows(st.session_state, manual_df)
        if deleted_count:
            st.success(f"已删除 {deleted_count} 行。")
            st.rerun()
        else:
            st.info("请先在表格第一列勾选要删除的行。")
with action_col4:
    if st.button("重置示例", use_container_width=True):
        reset_manual_metadata_rows(st.session_state)
        st.rerun()

manual_base_filename = st.text_input(
    "保存文件名",
    value="manual_metadata",
    help="系统会自动添加随机后缀，避免覆盖已有文件。",
)
if st.button("保存手工录入为当前输入", use_container_width=True):
    apply_manual_metadata_editor_changes(st.session_state, manual_df)
    manual_records = editor_dataframe_to_manual_records(manual_df)
    try:
        manual_path = save_manual_metadata_records(
            manual_records,
            output_dir=UPLOAD_OUTPUT_DIR,
            base_filename=manual_base_filename,
        )
    except Exception as exc:
        st.error(f"保存手工录入元数据失败: {exc}")
    else:
        manual_bytes = Path(manual_path).read_bytes()
        manual_signature = content_signature(manual_bytes)
        set_uploaded_file_state(
            file_path=manual_path,
            file_name=Path(manual_path).name,
            file_size=len(manual_bytes),
            file_extension="csv",
            file_signature=manual_signature,
            source_label="manual_metadata",
        )
        st.success("手工录入元数据已保存，并设为当前输入。")
        ensure_large_file_runtime_ready(manual_path, manual_signature)

file_path = get_uploaded_file_path()
if file_path:
    agent_session_id = ensure_agent_shell_session_id()
    set_last_uploaded_file(agent_session_id, file_path)

    st.subheader("当前输入文件")
    render_metric_row(
        [
            ("文件名", get_uploaded_file_name() or "N/A"),
            ("文件大小(字节)", get_uploaded_file_size() or 0),
            ("扩展名", get_uploaded_file_extension() or "N/A"),
        ],
    )
    st.caption(f"本地路径: {file_path}")
    st.caption(f"共享会话: {agent_session_id}")

    st.subheader("元数据学习库")
    st.caption("如果当前文件质量较好，可以将已填写的中文名和描述学习到本地记忆库，供后续新文件自动补全优先参考。")
    learning_confirmed = st.checkbox(
        "我确认当前文件可作为高质量学习样本",
        value=False,
        key="metadata_learning_confirmed",
    )
    if st.button("学习当前元数据", use_container_width=True):
        if not learning_confirmed:
            st.warning("请先确认当前文件可作为高质量学习样本。")
            st.stop()
        try:
            learning_summary = learn_metadata_memory_from_file(file_path)
        except Exception as exc:
            st.error(f"学习元数据失败: {exc}")
        else:
            st.success(
                "元数据学习完成："
                f"字段记忆 {learning_summary.field_memory_count} 条，"
                f"表记忆 {learning_summary.table_memory_count} 条。"
            )

    st.subheader("元数据自动补全")
    st.caption("算法每个缺失项给出 3 个候选值；必须人工选择或编辑最终值并确认审核后，才会保存为增强版 CSV。")
    completion_col1, completion_col2 = st.columns([1, 1])
    with completion_col1:
        if st.button("预览自动补全", use_container_width=True):
            try:
                completion_result = complete_metadata_file(file_path)
            except Exception as exc:
                st.error(f"自动补全失败: {exc}")
            else:
                st.session_state["metadata_completion_result"] = completion_result
                st.success(f"已生成 {completion_result.completed_count} 条补全建议。")

    completion_result = st.session_state.get("metadata_completion_result")
    if completion_result is not None:
        changes_df = metadata_completion_changes_to_dataframe(completion_result.changes)
        if changes_df.empty:
            st.info("暂无可补全的缺失项。")
            reviewed_changes_df = changes_df
        else:
            review_df = changes_df.copy()
            review_df.insert(0, "accept", False)
            review_df.insert(1, "selected_candidate", "候选1")
            reviewed_changes_df = st.data_editor(
                review_df,
                use_container_width=True,
                hide_index=True,
                key="metadata_completion_review_editor",
                column_config={
                    "accept": st.column_config.CheckboxColumn(
                        "保存",
                        help="只有勾选保存的最终采纳值才会写入增强版元数据。",
                        default=False,
                    ),
                    "selected_candidate": st.column_config.SelectboxColumn(
                        "候选选择",
                        options=["候选1", "候选2", "候选3", "人工编辑"],
                        help="选择候选值后，可继续修改最终采纳值。",
                    ),
                    "final_value": st.column_config.TextColumn(
                        "最终采纳值",
                        help="可直接编辑。保存时以这里的值为准。",
                    ),
                },
            )
            accepted_count = int(reviewed_changes_df["accept"].fillna(False).sum())
            st.caption(f"已选择保存 {accepted_count} / {len(reviewed_changes_df)} 条建议。")
        review_confirmed = st.checkbox(
            "我已人工审核所选补全建议",
            value=False,
            key="metadata_completion_review_confirmed",
        )
        with completion_col2:
            if st.button("保存已审核采纳项为当前输入", use_container_width=True):
                accepted_values = {}
                if not reviewed_changes_df.empty:
                    selected_rows = reviewed_changes_df[
                        reviewed_changes_df["accept"].fillna(False)
                    ]
                    for _, review_row in selected_rows.iterrows():
                        selected_candidate = str(
                            review_row.get("selected_candidate") or "人工编辑"
                        )
                        final_value = review_row.get("final_value")
                        if selected_candidate == "候选1":
                            final_value = review_row.get("candidate_1")
                        elif selected_candidate == "候选2":
                            final_value = review_row.get("candidate_2")
                        elif selected_candidate == "候选3":
                            final_value = review_row.get("candidate_3")
                        if str(final_value or "").strip():
                            accepted_values[str(review_row["change_key"])] = str(
                                final_value
                            ).strip()
                if not review_confirmed:
                    st.warning("请先确认已经人工审核所选补全建议。")
                    st.stop()
                if not accepted_values:
                    st.warning("请至少勾选一条要保存的补全建议，并填写最终采纳值。")
                    st.stop()
                try:
                    reviewed_completion = apply_reviewed_completion_values(
                        completion_result.source_dataframe
                        if completion_result.source_dataframe is not None
                        else completion_result.dataframe,
                        completion_result.changes,
                        accepted_values,
                    )
                    saved_completion = save_completed_metadata(
                        reviewed_completion,
                        output_dir=UPLOAD_OUTPUT_DIR,
                        base_filename=Path(file_path).stem + "_completed",
                    )
                    learn_metadata_memory_from_dataframe(
                        reviewed_completion.dataframe,
                        source="reviewed_metadata_completion",
                    )
                except Exception as exc:
                    st.error(f"保存增强版元数据失败: {exc}")
                else:
                    if saved_completion.output_path:
                        completed_bytes = Path(saved_completion.output_path).read_bytes()
                        completed_signature = content_signature(completed_bytes)
                        set_uploaded_file_state(
                            file_path=saved_completion.output_path,
                            file_name=Path(saved_completion.output_path).name,
                            file_size=len(completed_bytes),
                            file_extension="csv",
                            file_signature=completed_signature,
                            source_label="metadata_completion",
                        )
                        st.session_state["metadata_completion_result"] = saved_completion
                        st.success("已保存人工审核采纳后的增强版元数据，并设为当前输入。")
                        ensure_large_file_runtime_ready(
                            saved_completion.output_path,
                            completed_signature,
                        )
                        st.rerun()

    render_workflow_run_panel(
        file_path,
        key_prefix="upload_quick_run",
        title="当前输入快捷运行",
    )

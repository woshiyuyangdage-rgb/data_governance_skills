"""Upload page for local metadata files."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import (
    INPUT_TEMPLATE_DOC_PATH,
    SAMPLE_METADATA_PATH,
    UPLOAD_OUTPUT_DIR,
    ensure_agent_shell_session_id,
    ensure_project_root_on_path,
    get_uploaded_file_extension,
    get_uploaded_file_name,
    get_uploaded_file_path,
    get_uploaded_file_signature,
    get_uploaded_file_size,
    initialize_session_state,
    restore_agent_session_to_state,
    set_uploaded_file_state,
)
from app.ui.column_labels import localize_dataframe_columns
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
    file_cache_key,
    read_csv_dataframe_cached,
    read_file_bytes_cached,
)

ensure_project_root_on_path()

from app.core.agent.session_store import (
    list_session_snapshots,
    load_latest_session_snapshot,
    set_last_uploaded_file,
)
from app.core.orchestrator.profile_loader import list_enabled_profiles
from app.core.parser.manual_metadata_input import save_manual_metadata_records
from app.core.utils.file_utils import get_file_extension, save_uploaded_file

initialize_session_state()

render_page_header(
    "上传元数据",
    "上传符合模板的本地 CSV 或 Excel 文件，或手工录入少量元数据，作为后续诊断与评审的输入。",
)

sample_cache_token = file_cache_key(str(SAMPLE_METADATA_PATH))
sample_bytes = read_file_bytes_cached(str(SAMPLE_METADATA_PATH), sample_cache_token)
sample_df = read_csv_dataframe_cached(str(SAMPLE_METADATA_PATH), sample_cache_token)

left, right = st.columns([2, 1])

with left:
    st.subheader("恢复入口")
    snapshots = list_session_snapshots()
    if snapshots and st.button("恢复最近会话状态", use_container_width=True):
        session = load_latest_session_snapshot()
        if session is None:
            st.warning("没有可恢复的会话快照。")
        else:
            restore_agent_session_to_state(session, source_label=str(snapshots[0]))
            st.success(f"已恢复会话 {session.session_id}")
    elif not snapshots:
        st.info("当前没有可恢复的会话快照。")

    if st.button("载入示例数据", use_container_width=True):
        sample_signature = content_signature(sample_bytes)
        set_uploaded_file_state(
            file_path=SAMPLE_METADATA_PATH,
            file_signature=sample_signature,
            source_label="sample_metadata",
        )
        st.success("示例数据已载入。")
        ensure_large_file_runtime_ready(str(SAMPLE_METADATA_PATH), sample_signature)

with right:
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

st.subheader("工作流配置")
for profile in list_enabled_profiles():
    st.markdown(
        f"- `{profile.name}`: {profile.description} "
        f"(stages: {', '.join(profile.stages)})"
    )

with st.expander("示例数据预览", expanded=True):
    st.dataframe(localize_dataframe_columns(sample_df), use_container_width=True)
    st.caption(f"示例文件: {SAMPLE_METADATA_PATH}")
    st.download_button(
        label="下载示例 CSV",
        data=sample_bytes,
        file_name=SAMPLE_METADATA_PATH.name,
        mime="text/csv",
        use_container_width=True,
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

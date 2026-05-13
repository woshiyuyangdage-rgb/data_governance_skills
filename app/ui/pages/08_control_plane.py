"""Lightweight governance control plane page."""

import json
from pathlib import Path
import sys

import pandas as pd
import streamlit as st
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.page_utils import ensure_project_root_on_path, initialize_session_state

ensure_project_root_on_path()

from app.core.control_plane.control_plane_service import ControlPlaneService

initialize_session_state()

service = ControlPlaneService()


def _serialize_content(asset_format: str, content: object) -> str:
    if asset_format == "yaml":
        return yaml.safe_dump(content or {}, allow_unicode=True, sort_keys=False)
    if asset_format == "json":
        return json.dumps(content or {}, ensure_ascii=False, indent=2)
    if asset_format == "csv":
        dataframe = pd.DataFrame(content or [])
        return dataframe.to_csv(index=False)
    return str(content)


def _render_preview(asset_format: str, content: object) -> None:
    if asset_format == "csv":
        dataframe = pd.DataFrame(content or [])
        if dataframe.empty:
            st.info("CSV asset is currently empty.")
        else:
            st.dataframe(dataframe, use_container_width=True)
        return
    st.json(content)


st.title("Governance Control Plane")
st.write(
    "Manage local governance configuration assets in one place. You can inspect, "
    "edit, validate, save, and publish dictionaries, workflow profiles, intent "
    "patterns, and tool registry content."
)

asset_rows = service.list_assets_with_status()
asset_lookup = {row["asset_name"]: row for row in asset_rows}
asset_names = list(asset_lookup.keys())

if not asset_names:
    st.warning("No managed config assets are registered.")
else:
    selected_asset_name = st.selectbox("Managed Asset", options=asset_names)
    asset_payload = service.get_asset_content(selected_asset_name)
    asset = asset_payload["asset"]
    status = asset_payload["status"]
    asset_format = str(asset_payload["format"])
    content = asset_payload["content"]

    st.caption(
        f"Type: {asset['asset_type']} | File: {asset['file_path']} | Editable: {asset['editable']}"
    )

    metric_status, metric_validated, metric_published = st.columns(3)
    metric_status.metric("Status", status.get("current_status") or "unknown")
    metric_validated.metric(
        "Last Validated",
        status.get("last_validated_at") or "N/A",
    )
    metric_published.metric(
        "Last Published",
        status.get("last_published_at") or "N/A",
    )
    if status.get("last_error_message"):
        st.error(status["last_error_message"])

    with st.expander("Current Content Preview", expanded=True):
        _render_preview(asset_format, content)

    editor_value = _serialize_content(asset_format, content)
    edited_text = st.text_area(
        "Editable Content",
        value=editor_value,
        height=360,
        key=f"control_plane_editor_{selected_asset_name}",
    )

    button_col1, button_col2, button_col3 = st.columns(3)
    if button_col1.button("Validate", use_container_width=True):
        try:
            validation_result = service.validate_asset_preview(
                selected_asset_name,
                edited_text,
            )
        except Exception as exc:
            st.error(f"Failed to validate asset preview: {exc}")
        else:
            st.session_state["latest_control_plane_result"] = validation_result
            if validation_result.is_valid:
                st.success("Validation passed for the current editor content.")
            else:
                st.error("Validation failed for the current editor content.")

    if button_col2.button("Save", type="primary", use_container_width=True):
        try:
            save_result = service.save_asset(selected_asset_name, edited_text)
        except Exception as exc:
            st.error(f"Failed to save asset: {exc}")
        else:
            st.session_state["latest_control_plane_result"] = save_result
            if save_result.status in {"draft", "published"}:
                st.success(save_result.message)
            else:
                st.error(save_result.message)
            st.rerun()

    if button_col3.button("Publish", use_container_width=True):
        try:
            publish_result = service.publish_asset(selected_asset_name)
        except Exception as exc:
            st.error(f"Failed to publish asset: {exc}")
        else:
            st.session_state["latest_control_plane_result"] = publish_result
            if publish_result.status == "published":
                st.success(publish_result.message)
            else:
                st.error(publish_result.message)
            st.rerun()

    latest_result = st.session_state.get("latest_control_plane_result")
    if latest_result is not None:
        st.subheader("Latest Result")
        if hasattr(latest_result, "model_dump"):
            st.json(latest_result.model_dump())
        else:
            st.write(latest_result)

        validation_payload = None
        if hasattr(latest_result, "validation_result") and latest_result.validation_result is not None:
            validation_payload = latest_result.validation_result
        elif hasattr(latest_result, "is_valid"):
            validation_payload = latest_result

        if validation_payload is not None:
            st.subheader("Validation Messages")
            messages = list(getattr(validation_payload, "messages", []))
            warnings = list(getattr(validation_payload, "warnings", []))
            if messages:
                for message in messages:
                    st.error(message)
            if warnings:
                for warning in warnings:
                    st.warning(warning)
            if not messages and not warnings:
                st.success("No validation errors or warnings were returned.")

    st.subheader("Recent Backups")
    backups = service.list_asset_backups(selected_asset_name)
    if not backups:
        st.info("No backups are available yet for this asset.")
    else:
        for backup_path in backups[:10]:
            st.write(f"- `{backup_path}`")

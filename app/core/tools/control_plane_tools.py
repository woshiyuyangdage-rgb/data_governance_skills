"""Control-plane tool handlers for the governance executor."""

from app.core.models.tool_call_response import ToolCallResponse


class ControlPlaneToolMixin:
    """Tool handlers for managed configuration assets."""

    def list_config_assets(self, arguments: dict[str, object]) -> ToolCallResponse:
        """List managed control-plane assets and their current status."""
        tool_name = "list_config_assets"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation="list",
        )
        try:
            assets = self.control_plane_service.list_assets_with_status()
            trace = self._finish_trace(
                trace,
                "success",
                "Managed config assets were listed successfully.",
                operation="list",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Managed config assets were listed successfully.",
                assets,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to list config assets: {exc}",
                operation="list",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to list config assets.",
                None,
                trace,
            )

    def get_config_asset(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Return one managed control-plane asset with its current content."""
        tool_name = "get_config_asset"
        asset_name = self._optional_string(arguments, "asset_name") or "unknown_asset"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            asset_name=asset_name,
            operation="get",
        )
        try:
            if asset_name == "unknown_asset":
                raise ValueError("Argument 'asset_name' is required.")
            asset_payload = self.control_plane_service.get_asset_content(asset_name)
            trace = self._finish_trace(
                trace,
                "success",
                f"Managed config asset '{asset_name}' was loaded successfully.",
                asset_name=asset_name,
                operation="get",
            )
            return self._build_tool_response(
                tool_name,
                "success",
                f"Managed config asset '{asset_name}' was loaded successfully.",
                asset_payload,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to get config asset '{asset_name}': {exc}",
                asset_name=asset_name,
                operation="get",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or f"Failed to get config asset '{asset_name}'.",
                None,
                trace,
            )

    def validate_config_asset(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Validate one managed control-plane asset."""
        tool_name = "validate_config_asset"
        asset_name = self._optional_string(arguments, "asset_name") or "unknown_asset"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            asset_name=asset_name,
            operation="validate",
        )
        try:
            if asset_name == "unknown_asset":
                raise ValueError("Argument 'asset_name' is required.")
            validation_result = self.control_plane_service.validate_asset(asset_name)
            trace = self._finish_trace(
                trace,
                "success" if validation_result.is_valid else "invalid",
                (
                    f"Managed config asset '{asset_name}' is valid."
                    if validation_result.is_valid
                    else f"Managed config asset '{asset_name}' is invalid."
                ),
                asset_name=asset_name,
                operation="validate",
                validation_status="valid" if validation_result.is_valid else "invalid",
            )
            return self._build_tool_response(
                tool_name,
                "success" if validation_result.is_valid else "invalid",
                trace.message or f"Validation completed for asset '{asset_name}'.",
                validation_result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to validate config asset '{asset_name}': {exc}",
                asset_name=asset_name,
                operation="validate",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or f"Failed to validate config asset '{asset_name}'.",
                None,
                trace,
            )

    def save_config_asset(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Save one managed control-plane asset after validation."""
        tool_name = "save_config_asset"
        asset_name = self._optional_string(arguments, "asset_name") or "unknown_asset"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            asset_name=asset_name,
            operation="save",
        )
        try:
            if asset_name == "unknown_asset":
                raise ValueError("Argument 'asset_name' is required.")
            if "content" not in arguments:
                raise ValueError("Argument 'content' is required.")
            result = self.control_plane_service.save_asset(
                asset_name,
                arguments.get("content"),
            )
            validation_status = None
            if result.validation_result is not None:
                validation_status = (
                    "valid" if result.validation_result.is_valid else "invalid"
                )
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                asset_name=asset_name,
                operation="save",
                validation_status=validation_status,
                notes=(
                    [f"Backup created at {result.backup_path}"]
                    if result.backup_path
                    else []
                ),
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to save config asset '{asset_name}': {exc}",
                asset_name=asset_name,
                operation="save",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or f"Failed to save config asset '{asset_name}'.",
                None,
                trace,
            )

    def publish_config_asset(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Publish one managed control-plane asset."""
        tool_name = "publish_config_asset"
        asset_name = self._optional_string(arguments, "asset_name") or "unknown_asset"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            asset_name=asset_name,
            operation="publish",
        )
        try:
            if asset_name == "unknown_asset":
                raise ValueError("Argument 'asset_name' is required.")
            result = self.control_plane_service.publish_asset(asset_name)
            validation_status = None
            if result.validation_result is not None:
                validation_status = (
                    "valid" if result.validation_result.is_valid else "invalid"
                )
            trace = self._finish_trace(
                trace,
                result.status,
                result.message,
                asset_name=asset_name,
                operation="publish",
                validation_status=validation_status,
            )
            return self._build_tool_response(
                tool_name,
                result.status,
                result.message,
                result.model_dump(),
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to publish config asset '{asset_name}': {exc}",
                asset_name=asset_name,
                operation="publish",
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or f"Failed to publish config asset '{asset_name}'.",
                None,
                trace,
            )

"""Tool handlers for local learning-memory maintenance."""

from app.core.models.tool_call_response import ToolCallResponse


class LearningMemoryToolMixin:
    """Tool handlers for learned-memory health, backups, and rebuilds."""

    def learning_health(self, arguments: dict[str, object]) -> ToolCallResponse:
        """Return a combined learning-memory health summary."""
        tool_name = "learning_health"
        operation = "learning_health"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            health = self.learning_health_service.summarize().model_dump()
            trace = self._finish_trace(
                trace,
                "success",
                "Learning-memory health summary was built successfully.",
                operation=operation,
                notes=[
                    f"total_memory_count={health.get('total_memory_count')}",
                    f"invalid_record_count={health.get('total_invalid_record_count')}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Learning-memory health summary was built successfully.",
                health,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build learning-memory health summary: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build learning-memory health summary.",
                None,
                trace,
            )

    def learning_health_details(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Return learned-memory records that need maintenance attention."""
        tool_name = "learning_health_details"
        operation = "learning_health_details"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            details = self.learning_health_service.details()
            trace = self._finish_trace(
                trace,
                "success",
                "Learning-memory health details were loaded successfully.",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Learning-memory health details were loaded successfully.",
                details,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to load learning-memory health details: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to load learning-memory health details.",
                None,
                trace,
            )

    def learning_maintenance_report(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Return a consolidated maintenance report for local learning memory."""
        tool_name = "learning_maintenance_report"
        operation = "learning_maintenance_report"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            report = self.learning_health_service.maintenance_report(
                backup_limit=int(arguments.get("backup_limit", 3) or 3),
            )
            recommendations = report.get("recommendations", [])
            recommendation_count = (
                len(recommendations) if isinstance(recommendations, list) else 0
            )
            trace = self._finish_trace(
                trace,
                "success",
                "Learning-memory maintenance report was built successfully.",
                operation=operation,
                notes=[f"recommendation_count={recommendation_count}"],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Learning-memory maintenance report was built successfully.",
                report,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to build learning-memory maintenance report: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to build learning-memory maintenance report.",
                None,
                trace,
            )

    def export_learning_maintenance_report(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Export a learning-memory maintenance report as local files."""
        tool_name = "export_learning_maintenance_report"
        operation = "export_learning_maintenance_report"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            result = self.learning_health_service.export_maintenance_report(
                backup_limit=int(arguments.get("backup_limit", 3) or 3),
                output_dir=self._optional_string(arguments, "output_dir"),
                base_filename=self._optional_string(arguments, "base_filename"),
            )
            artifact_count = int(result.get("artifact_count") or 0)
            trace = self._finish_trace(
                trace,
                result.get("status", "success"),
                str(result.get("summary") or "Learning-memory report exported."),
                operation=operation,
                generated_file_count=artifact_count,
                delivery_output_dir=str(result.get("output_dir") or ""),
            )
            return self._build_tool_response(
                tool_name,
                str(result.get("status", "success")),
                str(result.get("summary") or "Learning-memory report exported."),
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to export learning-memory maintenance report: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to export learning-memory maintenance report.",
                None,
                trace,
            )

    def create_learning_memory_backup(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Create a timestamped backup package for local learning memory."""
        tool_name = "create_learning_memory_backup"
        operation = "create_learning_memory_backup"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            backup = self.learning_health_service.create_backup()
            backup_id = str(backup.get("backup_id") or "")
            trace = self._finish_trace(
                trace,
                "success",
                f"Learning-memory backup '{backup_id}' was created successfully.",
                operation=operation,
                notes=[f"backup_id={backup_id}"],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                f"Learning-memory backup '{backup_id}' was created successfully.",
                backup,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to create learning-memory backup: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to create learning-memory backup.",
                None,
                trace,
            )

    def list_learning_memory_backups(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """List local learning-memory backup packages, newest first."""
        tool_name = "list_learning_memory_backups"
        operation = "list_learning_memory_backups"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            backups = self.learning_health_service.list_backups()
            trace = self._finish_trace(
                trace,
                "success",
                "Learning-memory backups were listed successfully.",
                operation=operation,
                notes=[f"backup_count={len(backups)}"],
            )
            return self._build_tool_response(
                tool_name,
                "success",
                "Learning-memory backups were listed successfully.",
                backups,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to list learning-memory backups: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to list learning-memory backups.",
                None,
                trace,
            )

    def validate_learning_memory_backup(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Validate one local learning-memory backup package."""
        tool_name = "validate_learning_memory_backup"
        operation = "validate_learning_memory_backup"
        backup_id = self._optional_string(arguments, "backup_id") or "unknown_backup"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            asset_name=backup_id,
            operation=operation,
        )
        try:
            if backup_id == "unknown_backup":
                raise ValueError("Argument 'backup_id' is required.")
            validation = self.learning_health_service.validate_backup(backup_id)
            is_valid = bool(validation.get("is_valid"))
            trace = self._finish_trace(
                trace,
                "success" if is_valid else "invalid",
                (
                    f"Learning-memory backup '{backup_id}' is valid."
                    if is_valid
                    else f"Learning-memory backup '{backup_id}' is invalid."
                ),
                asset_name=backup_id,
                operation=operation,
                validation_status="valid" if is_valid else "invalid",
            )
            return self._build_tool_response(
                tool_name,
                "success" if is_valid else "invalid",
                trace.message or f"Validation completed for backup '{backup_id}'.",
                validation,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to validate learning-memory backup '{backup_id}': {exc}",
                asset_name=backup_id,
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message
                or f"Failed to validate learning-memory backup '{backup_id}'.",
                None,
                trace,
            )

    def backup_then_prune_invalid_learning_memory(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Back up local learning memory before pruning invalid records."""
        tool_name = "backup_then_prune_invalid_learning_memory"
        operation = "backup_then_prune_invalid_learning_memory"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            result = self.learning_health_service.backup_then_prune_invalid()
            removed_count = int(result.get("removed_count") or 0)
            trace = self._finish_trace(
                trace,
                result.get("status", "success"),
                str(result.get("summary") or "Invalid learning-memory records pruned."),
                operation=operation,
                notes=[f"removed_count={removed_count}"],
            )
            return self._build_tool_response(
                tool_name,
                str(result.get("status", "success")),
                str(result.get("summary") or "Invalid learning-memory records pruned."),
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to back up and prune invalid learning memory: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message
                or "Failed to back up and prune invalid learning memory.",
                None,
                trace,
            )

    def rebuild_review_learning(
        self,
        arguments: dict[str, object],
    ) -> ToolCallResponse:
        """Rebuild learning memory from saved human review records."""
        tool_name = "rebuild_review_learning"
        operation = "rebuild_review_learning"
        trace = self._start_trace(
            tool_name=tool_name,
            arguments=arguments,
            session_id=self._optional_string(arguments, "session_id"),
            operation=operation,
        )
        try:
            raw_memory_types = arguments.get("memory_types")
            if raw_memory_types is not None and not isinstance(raw_memory_types, list):
                raise ValueError("Argument 'memory_types' must be a list when provided.")
            result = self.learning_health_service.rebuild_review_learning(
                raw_memory_types,
                create_backup=bool(arguments.get("create_backup", True)),
            )
            trace = self._finish_trace(
                trace,
                result.get("status", "success"),
                str(result.get("summary") or "Review-based learning memory rebuilt."),
                operation=operation,
                notes=[
                    f"memory_types={','.join(result.get('memory_types', []))}",
                    f"total_learned_count={result.get('total_learned_count')}",
                ],
            )
            return self._build_tool_response(
                tool_name,
                str(result.get("status", "success")),
                str(result.get("summary") or "Review-based learning memory rebuilt."),
                result,
                trace,
            )
        except Exception as exc:
            trace = self._finish_trace(
                trace,
                "failed",
                f"Failed to rebuild review-based learning memory: {exc}",
                operation=operation,
            )
            return self._build_tool_response(
                tool_name,
                "failed",
                trace.message or "Failed to rebuild review-based learning memory.",
                None,
                trace,
            )

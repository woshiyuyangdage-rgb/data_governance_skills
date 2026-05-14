"""Build rerun scope from confirmation workbook round-trip results."""

from app.core.models.confirmation_roundtrip_result import ConfirmationRoundTripResult


class RoundTripRerunService:
    """Summarize changed objects from imported confirmation workbooks."""

    @staticmethod
    def build_rerun_scope_from_roundtrip(
        roundtrip_results: list[ConfirmationRoundTripResult],
    ) -> dict[str, object]:
        """Build a changed-object scope payload for optional rerun."""
        changed_objects = sorted(
            {
                object_key
                for result in roundtrip_results
                for object_key in result.changed_object_keys
            }
        )
        return {
            "rerun_changed_only": True,
            "rerun_object_count": len(changed_objects),
            "changed_object_count": len(changed_objects),
            "changed_object_keys": changed_objects,
        }

    @staticmethod
    def summarize_roundtrip_changed_objects(
        roundtrip_results: list[ConfirmationRoundTripResult],
    ) -> dict[str, object]:
        """Summarize changed objects by workbook type."""
        by_workbook_type = {
            result.workbook_type: len(result.changed_object_keys)
            for result in roundtrip_results
        }
        scope = RoundTripRerunService.build_rerun_scope_from_roundtrip(roundtrip_results)
        return {
            "changed_object_count": scope["changed_object_count"],
            "changed_object_keys": scope["changed_object_keys"],
            "by_workbook_type": by_workbook_type,
        }


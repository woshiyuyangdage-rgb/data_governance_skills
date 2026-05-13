"""Incremental fingerprint comparison service."""

from app.core.models.incremental_diff_item import IncrementalDiffItem
from app.core.models.incremental_diff_summary import IncrementalDiffSummary
from app.core.models.object_fingerprint import ObjectFingerprint


class IncrementalDiffService:
    """Compare old and new fingerprints and select rerun scope."""

    @staticmethod
    def _key(item: ObjectFingerprint) -> tuple[str, str]:
        return (item.object_type, item.object_name)

    def compare_fingerprints(
        self,
        old_fingerprints: list[ObjectFingerprint],
        new_fingerprints: list[ObjectFingerprint],
        pending_review_objects: list[str] | None = None,
    ) -> list[IncrementalDiffItem]:
        """Compare two fingerprint sets and classify object-level changes."""
        pending = set(pending_review_objects or [])
        old_map = {self._key(item): item for item in old_fingerprints}
        new_map = {self._key(item): item for item in new_fingerprints}
        diff_items: list[IncrementalDiffItem] = []

        for key, new_item in sorted(new_map.items()):
            old_item = old_map.get(key)
            if old_item is None:
                diff_type = "new"
                reason = "Object is new in the current metadata snapshot."
            elif new_item.object_name in pending:
                diff_type = "pending_review"
                reason = "Object is still pending review or confirmation."
            elif old_item.fingerprint != new_item.fingerprint:
                diff_type = "changed"
                reason = "Object fingerprint changed since the latest snapshot."
            else:
                diff_type = "unchanged"
                reason = "Object fingerprint is unchanged."
            diff_items.append(
                IncrementalDiffItem(
                    object_type=new_item.object_type,
                    object_name=new_item.object_name,
                    group_name=new_item.group_name,
                    diff_type=diff_type,
                    reason=reason,
                    old_fingerprint=old_item.fingerprint if old_item else None,
                    new_fingerprint=new_item.fingerprint,
                )
            )

        for key, old_item in sorted(old_map.items()):
            if key in new_map:
                continue
            diff_items.append(
                IncrementalDiffItem(
                    object_type=old_item.object_type,
                    object_name=old_item.object_name,
                    group_name=old_item.group_name,
                    diff_type="removed",
                    reason="Object existed in the latest snapshot but is absent now.",
                    old_fingerprint=old_item.fingerprint,
                    new_fingerprint=None,
                )
            )
        return diff_items

    @staticmethod
    def build_incremental_diff_summary(
        diff_items: list[IncrementalDiffItem],
    ) -> IncrementalDiffSummary:
        """Build counts for all diff categories."""
        counts = {
            "new": 0,
            "changed": 0,
            "unchanged": 0,
            "removed": 0,
            "pending_review": 0,
        }
        for item in diff_items:
            if item.diff_type in counts:
                counts[item.diff_type] += 1
        total_objects = len(diff_items)
        return IncrementalDiffSummary(
            total_objects=total_objects,
            new_count=counts["new"],
            changed_count=counts["changed"],
            unchanged_count=counts["unchanged"],
            removed_count=counts["removed"],
            pending_review_count=counts["pending_review"],
            summary=(
                f"{counts['new']} new, {counts['changed']} changed, "
                f"{counts['unchanged']} unchanged, {counts['removed']} removed, "
                f"{counts['pending_review']} pending review."
            ),
        )

    @staticmethod
    def filter_changed_objects(
        diff_items: list[IncrementalDiffItem],
    ) -> list[IncrementalDiffItem]:
        """Return objects that should be included in changed-only rerun."""
        return [
            item
            for item in diff_items
            if item.diff_type in {"new", "changed", "pending_review"}
        ]


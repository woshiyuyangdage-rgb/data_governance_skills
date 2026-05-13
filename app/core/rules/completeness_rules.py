"""Completeness rule placeholders for metadata governance."""

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta


class CompletenessRuleChecker:
    """Placeholder interface for completeness validation rules."""

    def check(self, table_meta: TableMeta) -> list[Issue]:
        # TODO: define completeness expectations for names, descriptions, and fields.
        raise NotImplementedError("Completeness rule checks are not implemented yet.")


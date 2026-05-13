"""Naming rule placeholders for metadata governance."""

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta


class NamingRuleChecker:
    """Placeholder interface for naming convention validation."""

    def check(self, table_meta: TableMeta) -> list[Issue]:
        # TODO: load naming rules from configuration and evaluate table/field names.
        raise NotImplementedError("Naming rule checks are not implemented yet.")


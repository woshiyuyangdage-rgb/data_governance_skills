"""Technical object identification rule placeholders."""

from app.core.models.issue import Issue
from app.core.models.table_meta import TableMeta


class TechnicalRuleChecker:
    """Placeholder interface for technical object identification rules."""

    def check(self, table_meta: TableMeta) -> list[Issue]:
        # TODO: implement keyword-based and pattern-based technical object checks.
        raise NotImplementedError("Technical rule checks are not implemented yet.")


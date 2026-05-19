"""Readiness, backlog, portfolio, and progress snapshot tool handlers."""

from app.core.tools.governance_lifecycle_backlog_tools import (
    GovernanceBacklogToolMixin,
)
from app.core.tools.governance_lifecycle_portfolio_tools import (
    GovernancePortfolioToolMixin,
)
from app.core.tools.governance_lifecycle_readiness_tools import (
    GovernanceReadinessToolMixin,
)


class GovernanceLifecycleToolMixin(
    GovernanceReadinessToolMixin,
    GovernanceBacklogToolMixin,
    GovernancePortfolioToolMixin,
):
    """Tool handlers for governance readiness, backlog, and portfolio flows."""

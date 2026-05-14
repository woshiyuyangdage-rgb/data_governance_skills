"""Standard local executor for governance tool contracts."""

from app.core.agent.agent_shell_service import AgentShellService
from app.core.control_plane.control_plane_service import ControlPlaneService
from app.core.tools.agent_tools import AgentToolMixin
from app.core.tools.base_executor import GovernanceToolExecutorBase
from app.core.tools.control_plane_tools import ControlPlaneToolMixin
from app.core.tools.delivery_tools import DeliveryToolMixin
from app.core.tools.dispatch_tools import ToolDispatchMixin
from app.core.tools.governance_lifecycle_tools import GovernanceLifecycleToolMixin
from app.core.tools.profile_tools import ProfileToolMixin
from app.core.tools.quality_tools import QualityToolMixin
from app.core.tools.template_intake_tools import TemplateIntakeToolMixin


class GovernanceToolExecutor(
    ToolDispatchMixin,
    ProfileToolMixin,
    AgentToolMixin,
    DeliveryToolMixin,
    QualityToolMixin,
    TemplateIntakeToolMixin,
    GovernanceLifecycleToolMixin,
    ControlPlaneToolMixin,
    GovernanceToolExecutorBase,
):
    """Execute standardized governance tools with local audit traces."""

    def __init__(self) -> None:
        self.agent_shell_service = AgentShellService()
        self.control_plane_service = ControlPlaneService()

"""L3 Rogue Agent attack implementation."""

from __future__ import annotations

from ..common import WorkflowL3StaticAttack


class RogueAgentAttack(WorkflowL3StaticAttack):
    """Workflow probes for trusted internal agents that violate policy."""

    risk_type = "rogue_agent"
    level = "l3"
    metadata_key = "rogue_agent"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the rogue agent attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Rogue Agent",
                "description": (
                    "System-level MAS probes for trusted internal agents that violate policy."
                ),
            }
        )
        return info

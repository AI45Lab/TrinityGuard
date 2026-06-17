"""L3 Insufficient Monitoring attack implementation."""

from __future__ import annotations

from ..common import WorkflowL3StaticAttack


class InsufficientMonitoringAttack(WorkflowL3StaticAttack):
    """Workflow probes for distributed monitoring blind spots."""

    risk_type = "insufficient_monitoring"
    level = "l3"
    metadata_key = "insufficient_monitoring"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the insufficient monitoring attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Insufficient Monitoring",
                "description": ("System-level MAS probes for distributed monitoring blind spots."),
            }
        )
        return info

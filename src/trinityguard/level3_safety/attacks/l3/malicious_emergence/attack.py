"""L3 Malicious Emergence attack implementation."""

from __future__ import annotations

from ..common import WorkflowL3StaticAttack


class MaliciousEmergenceAttack(WorkflowL3StaticAttack):
    """Workflow probes for harmful emergent collective behavior."""

    risk_type = "malicious_emergence"
    level = "l3"
    metadata_key = "malicious_emergence"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the malicious emergence attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Malicious Emergence",
                "description": (
                    "System-level MAS probes for harmful emergent collective behavior."
                ),
            }
        )
        return info

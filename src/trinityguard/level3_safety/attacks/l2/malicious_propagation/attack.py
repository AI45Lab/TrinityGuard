"""L2 malicious propagation attack implementation."""

from __future__ import annotations

from ..common import WorkflowL2StaticAttack


class MaliciousPropagationAttack(WorkflowL2StaticAttack):
    """Workflow probes for self-replicating or viral inter-agent payloads."""

    risk_type = "malicious_propagation"
    level = "l2"
    metadata_key = "malicious_propagation"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the malicious propagation attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Malicious Propagation",
                "description": (
                    "Inter-agent workflow probes that test whether malicious instructions "
                    "replicate or propagate through normal MAS communication channels."
                ),
            }
        )
        return info

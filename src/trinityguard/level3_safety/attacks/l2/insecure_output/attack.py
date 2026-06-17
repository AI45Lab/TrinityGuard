"""L2 insecure output handling attack implementation."""

from __future__ import annotations

from ..common import WorkflowL2StaticAttack


class InsecureOutputAttack(WorkflowL2StaticAttack):
    """Workflow probes for unsafe downstream handling of agent outputs."""

    risk_type = "insecure_output"
    level = "l2"
    metadata_key = "insecure_output"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the insecure output attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Insecure Output Handling",
                "description": (
                    "Inter-agent workflow probes for unsafe handling of LLM output by "
                    "downstream agents, renderers, databases, shells, or tool-call parsers."
                ),
            }
        )
        return info

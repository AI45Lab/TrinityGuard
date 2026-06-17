"""L3 Group Hallucination attack implementation."""

from __future__ import annotations

from ..common import WorkflowL3StaticAttack


class GroupHallucinationAttack(WorkflowL3StaticAttack):
    """Workflow probes for false consensus and group hallucination."""

    risk_type = "group_hallucination"
    level = "l3"
    metadata_key = "group_hallucination"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the group hallucination attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Group Hallucination",
                "description": (
                    "System-level MAS probes for false consensus and group hallucination."
                ),
            }
        )
        return info

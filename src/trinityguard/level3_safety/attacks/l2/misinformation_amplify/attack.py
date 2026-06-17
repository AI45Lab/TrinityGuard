"""L2 misinformation amplification attack implementation."""

from __future__ import annotations

from ..common import WorkflowL2StaticAttack


class MisinformationAmplifyAttack(WorkflowL2StaticAttack):
    """Workflow probes for inter-agent amplification of false claims."""

    risk_type = "misinformation_amplify"
    level = "l2"
    metadata_key = "misinformation_amplify"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the misinformation amplification attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Misinformation Amplification",
                "description": (
                    "Inter-agent workflow probes that test whether initial false claims "
                    "are repeated, strengthened, or treated as consensus facts."
                ),
            }
        )
        return info

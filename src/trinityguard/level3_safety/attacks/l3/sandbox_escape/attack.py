"""L3 Sandbox Escape attack implementation."""

from __future__ import annotations

from ..common import WorkflowL3StaticAttack


class SandboxEscapeAttack(WorkflowL3StaticAttack):
    """Workflow probes for sandbox-boundary bypass chains."""

    risk_type = "sandbox_escape"
    level = "l3"
    metadata_key = "sandbox_escape"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the sandbox escape attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L3 Sandbox Escape",
                "description": ("System-level MAS probes for sandbox-boundary bypass chains."),
            }
        )
        return info

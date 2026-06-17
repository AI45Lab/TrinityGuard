"""L2 identity spoofing attack implementation."""

from __future__ import annotations

from ..common import WorkflowL2StaticAttack


class IdentitySpoofingAttack(WorkflowL2StaticAttack):
    """Workflow probes for spoofed agent or authority identities."""

    risk_type = "identity_spoofing"
    level = "l2"
    metadata_key = "identity_spoofing"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the identity spoofing attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Identity Spoofing",
                "description": (
                    "Inter-agent workflow probes that test whether agents trust spoofed "
                    "sender names, authority claims, chat-manager messages, or role prefixes."
                ),
            }
        )
        return info

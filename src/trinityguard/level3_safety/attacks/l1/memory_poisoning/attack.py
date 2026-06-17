"""L1 memory poisoning attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class MemoryPoisoningAttack(BaseAttack):
    """Static memory/context poisoning probes for single-agent targets."""

    risk_type = "memory_poisoning"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the memory poisoning attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Memory Poisoning",
                "description": (
                    "Prompts that test whether an agent accepts malicious memory updates, "
                    "false user-authority claims, poisoned retrieved facts, or "
                    "trigger-word backdoors."
                ),
            }
        )
        return info

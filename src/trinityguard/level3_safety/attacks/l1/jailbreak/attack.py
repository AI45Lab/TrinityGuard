"""L1 jailbreak attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class JailbreakAttack(BaseAttack):
    """Static jailbreak prompt attack based on declared dataset cases."""

    risk_type = "jailbreak"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the jailbreak attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Jailbreak",
                "description": (
                    "Direct prompt attacks that attempt to override an agent's "
                    "safety constraints through roleplay, fake authority, "
                    "multi-turn escalation, many-shot conditioning, or multilingual framing."
                ),
            }
        )
        return info

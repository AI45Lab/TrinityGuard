"""L1 tool misuse attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class ToolMisuseAttack(BaseAttack):
    """Static tool misuse probes for unsafe tool-call planning."""

    risk_type = "tool_misuse"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the tool misuse attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Tool Misuse",
                "description": (
                    "Prompts that test whether an agent proposes unsafe tool calls, "
                    "over-privileged parameters, tool-chain exfiltration, or TOCTOU-prone actions."
                ),
            }
        )
        return info

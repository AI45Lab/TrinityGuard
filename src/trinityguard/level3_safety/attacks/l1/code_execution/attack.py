"""L1 code execution attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class CodeExecutionAttack(BaseAttack):
    """Static code execution and unsafe code-generation probes."""

    risk_type = "code_execution"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the code execution attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Code Execution",
                "description": (
                    "Prompts that test whether an agent executes, emits, or assists with "
                    "dangerous code, shell commands, exploit scaffolds, or unsafe interpreter use."
                ),
            }
        )
        return info

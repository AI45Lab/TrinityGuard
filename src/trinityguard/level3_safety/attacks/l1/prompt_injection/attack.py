"""L1 prompt injection attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class PromptInjectionAttack(BaseAttack):
    """Static prompt injection attack based on declared dataset cases."""

    risk_type = "prompt_injection"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the prompt injection attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Prompt Injection",
                "description": (
                    "Direct and indirect prompt injection probes that hide override "
                    "instructions in user text, tool outputs, documents, or encoded payloads."
                ),
            }
        )
        return info

"""L1 sensitive disclosure attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class SensitiveDisclosureAttack(BaseAttack):
    """Static sensitive disclosure attack based on declared dataset cases."""

    risk_type = "sensitive_disclosure"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the sensitive disclosure attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Sensitive Disclosure",
                "description": (
                    "Extraction probes for system prompts, hidden context, credentials, "
                    "PII, and architecture details that should remain confidential."
                ),
            }
        )
        return info

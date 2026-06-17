"""L1 excessive agency attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class ExcessiveAgencyAttack(BaseAttack):
    """Static excessive agency attack based on declared dataset cases."""

    risk_type = "excessive_agency"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the excessive agency attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Excessive Agency",
                "description": (
                    "Prompts that test whether an agent performs destructive, "
                    "unauthorized, or over-scoped actions without appropriate confirmation."
                ),
            }
        )
        return info

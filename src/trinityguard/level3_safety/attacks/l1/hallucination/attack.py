"""L1 hallucination attack implementation."""

from __future__ import annotations

from ...base import BaseAttack


class HallucinationAttack(BaseAttack):
    """Static hallucination probes for unsupported factual claims."""

    risk_type = "hallucination"
    level = "l1"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the hallucination attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L1 Hallucination",
                "description": (
                    "Prompts that test whether an agent fabricates legal, medical, academic, "
                    "financial, mathematical, or source-grounded facts instead of "
                    "admitting uncertainty."
                ),
            }
        )
        return info

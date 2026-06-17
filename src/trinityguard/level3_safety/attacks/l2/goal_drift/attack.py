"""L2 goal drift attack implementation."""

from __future__ import annotations

from ..common import WorkflowL2StaticAttack


class GoalDriftAttack(WorkflowL2StaticAttack):
    """Workflow probes for gradual or semantic drift from the original goal."""

    risk_type = "goal_drift"
    level = "l2"
    metadata_key = "goal_drift"

    def get_attack_info(self) -> dict[str, str]:
        """Return metadata for the goal drift attack."""
        info = super().get_attack_info()
        info.update(
            {
                "name": "L2 Goal Drift",
                "description": (
                    "Inter-agent workflow probes that test whether a MAS preserves the "
                    "original user goal across scope creep, priority hijacking, and semantic drift."
                ),
            }
        )
        return info

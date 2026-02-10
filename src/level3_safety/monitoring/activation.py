"""Activation helpers for progressive monitoring."""

from typing import Dict, Set, Tuple, Any

from ..monitor_agents.base import BaseMonitorAgent


def apply_monitor_decision(
    available: Dict[str, BaseMonitorAgent],
    active_names: Set[str],
    decision: Dict[str, Any]
) -> Tuple[Set[str], Dict[str, Any]]:
    """Apply enable/disable decision to active set.

    Returns:
        (new_active_names, info)
    """
    enable = set(decision.get("enable", []) or [])
    disable = set(decision.get("disable", []) or [])

    enable = {m for m in enable if m in available}
    disable = {m for m in disable if m in available}

    new_active = (set(active_names) | enable) - disable
    newly_enabled = new_active - set(active_names)
    newly_disabled = set(active_names) - new_active

    for name in newly_enabled:
        available[name].reset()

    info = {
        "new_active": sorted(new_active),
        "newly_enabled": sorted(newly_enabled),
        "newly_disabled": sorted(newly_disabled),
        "reason": decision.get("reason", "")
    }
    return new_active, info

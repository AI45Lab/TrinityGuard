"""Minimal progressive monitoring compatibility helpers for Safety_MAS."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from trinityguard.level2_intermediary.structured_logging import AgentStepLog


class GlobalMonitorAgent:
    """Small coordinator for progressive monitor activation decisions.

    This compatibility implementation accepts an optional ``decision_provider``
    callback so tests and local integrations can drive monitor activation
    without introducing production telemetry or LLM dependencies.
    """

    def __init__(
        self,
        *,
        available_monitors: list[str],
        config: dict[str, Any] | None = None,
        decision_provider: Callable[[AgentStepLog, list[str]], dict[str, Any] | None] | None = None,
    ) -> None:
        self.available_monitors = list(available_monitors)
        self.config = config or {}
        self.decision_provider = decision_provider
        self.events_seen = 0

    def reset(self) -> None:
        """Reset coordinator state between workflow runs."""

        self.events_seen = 0

    def ingest(
        self,
        log_entry: AgentStepLog,
        *,
        active_monitors: list[str],
    ) -> dict[str, Any] | None:
        """Return a monitor activation decision, if configured."""

        self.events_seen += 1
        if self.decision_provider is None:
            return None
        return self.decision_provider(log_entry, active_monitors)


def apply_monitor_decision(
    *,
    available: dict[str, Any],
    active_names: set[str],
    decision: dict[str, Any],
) -> tuple[set[str], dict[str, list[str]]]:
    """Apply a progressive monitor decision to known monitor names only."""

    known = set(available)
    new_active = set(active_names) & known
    activated: list[str] = []
    deactivated: list[str] = []
    ignored: list[str] = []

    for name in decision.get("activate", []):
        if name in known:
            if name not in new_active:
                activated.append(name)
            new_active.add(name)
        else:
            ignored.append(name)

    for name in decision.get("deactivate", []):
        if name in known:
            if name in new_active:
                deactivated.append(name)
            new_active.discard(name)
        else:
            ignored.append(name)

    info = {
        "activated": sorted(activated),
        "deactivated": sorted(deactivated),
        "ignored": sorted(ignored),
    }
    return new_active, info

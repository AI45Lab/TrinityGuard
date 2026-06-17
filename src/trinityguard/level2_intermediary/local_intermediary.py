"""Framework-agnostic intermediary for BaseMAS workflows."""

from __future__ import annotations

from typing import Any

from trinityguard.level1_framework.base import BaseMAS
from trinityguard.utils.exceptions import IntermediaryError

from .base import MASIntermediary


class LocalMASIntermediary(MASIntermediary):
    """Minimal intermediary for BaseMAS implementations used in fixture tests.

    This class is intentionally small: it enables fixture workflow and hook-path
    execution for modernized Safety_MAS behavior without pretending to
    support framework-specific AG2 operations such as direct agent reply APIs or
    real tool injection.
    """

    def __init__(self, mas: BaseMAS) -> None:
        if not isinstance(mas, BaseMAS):
            raise IntermediaryError(f"Expected BaseMAS instance, got {type(mas)}")
        super().__init__(mas)

    def agent_chat(self, agent_name: str, message: str, history: list | None = None) -> str:
        """Run a local direct-chat style probe through the generic workflow contract.

        Generic ``BaseMAS`` implementations do not expose framework-native direct
        reply APIs.  For fixture risk tests, route the probe through
        ``run_workflow`` and return its output so built-in L1 attacks can execute
        against simple adapters without pretending to support framework-specific
        AG2 chat internals.
        """

        result = self.mas.run_workflow(message, target_agent=agent_name, history=history)
        if not result.success:
            raise IntermediaryError(result.error or "local agent_chat workflow failed")
        return "" if result.output is None else str(result.output)

    def simulate_agent_message(self, from_agent: str, to_agent: str, message: str) -> dict:
        """Apply registered L1 hooks to a synthetic inter-agent message."""

        hook_result = self.mas._apply_message_hooks_with_result(
            {"from": from_agent, "to": to_agent, "content": message}
        )
        if hook_result.action == "deny":
            return {
                "from": from_agent,
                "to": to_agent,
                "message_ref": hook_result.to_dict()["message"].get("content", ""),
                "response": None,
                "success": False,
                "delivery_denied": hook_result.to_dict(),
                "metadata": hook_result.to_dict()["message"],
            }

        processed = hook_result.message
        return {
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "response": processed.get("content"),
            "success": True,
            "metadata": processed,
        }

    def get_resource_usage(self, agent_name: str | None = None) -> dict[str, Any]:
        """Return placeholder resource usage for fixture workflows."""

        return {"agent_name": agent_name, "mode": "local", "api_calls": 0}

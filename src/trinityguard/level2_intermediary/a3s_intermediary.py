"""A3S Code-specific intermediary implementation."""

from __future__ import annotations

import os
import time
from typing import Any

from ..level1_framework.a3s.adapter import A3SCodeMAS
from ..utils.exceptions import IntermediaryError
from .base import MASIntermediary


class A3SIntermediary(MASIntermediary):
    """Level 2 operations for A3S Code-backed MAS adapters."""

    def __init__(self, mas: A3SCodeMAS) -> None:
        if not isinstance(mas, A3SCodeMAS):
            raise IntermediaryError(f"Expected A3SCodeMAS instance, got {type(mas)}")
        super().__init__(mas)
        self._api_call_counts: dict[str, int] = {}
        self._start_time = time.time()

    def agent_chat(self, agent_name: str, message: str, history: list | None = None) -> str:
        """Run a direct prompt through the A3S session for L1 tests."""

        self._api_call_counts[agent_name] = self._api_call_counts.get(agent_name, 0) + 1
        try:
            return self.mas.direct_prompt(agent_name, message, history=history)
        except Exception as exc:
            raise IntermediaryError(f"Failed to chat with A3S agent {agent_name}: {exc}") from exc

    def simulate_agent_message(self, from_agent: str, to_agent: str, message: str) -> dict:
        """Apply TrinityGuard hooks to a synthetic A3S inter-agent handoff."""

        hook_result = self.mas._apply_message_hooks_with_result(
            {
                "from": from_agent,
                "to": to_agent,
                "content": message,
                "metadata": {
                    "adapter": "a3s_code",
                    "transition": "synthetic_agent_message",
                    "route_complete": True,
                },
            }
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

        return {
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "response": hook_result.message.get("content"),
            "success": True,
            "metadata": hook_result.message,
        }

    def inject_tool_call(self, agent_name: str, tool_name: str, params: dict) -> dict:
        """Execute a direct A3S session tool call when available."""

        self.mas.get_agent(agent_name)
        self._api_call_counts[agent_name] = self._api_call_counts.get(agent_name, 0) + 1
        try:
            result = self.mas.run_tool(tool_name, params)
            return {
                "agent": agent_name,
                "tool": tool_name,
                "params": params,
                "success": True,
                "result": result,
            }
        except Exception as exc:
            return {
                "agent": agent_name,
                "tool": tool_name,
                "params": params,
                "success": False,
                "error": str(exc),
            }

    def inject_memory(
        self,
        agent_name: str,
        memory_content: str,
        memory_type: str = "context",
    ) -> bool:
        """Inject adapter-local memory for a TrinityGuard test path."""

        return self.mas.add_memory(agent_name, memory_content, memory_type)

    def broadcast_message(self, from_agent: str, to_agents: list[str], message: str) -> dict:
        """Broadcast a synthetic message to several A3S worker specs."""

        return {
            to_agent: self.simulate_agent_message(from_agent, to_agent, message)
            for to_agent in to_agents
        }

    def spoof_identity(
        self,
        real_agent: str,
        spoofed_agent: str,
        to_agent: str,
        message: str,
    ) -> dict:
        """Send a synthetic message with claimed sender metadata."""

        hook_result = self.mas._apply_message_hooks_with_result(
            {
                "from": real_agent,
                "to": to_agent,
                "content": message,
                "name": spoofed_agent,
                "role": "assistant",
                "metadata": {
                    "adapter": "a3s_code",
                    "claimed_sender": spoofed_agent,
                    "real_sender": real_agent,
                    "transition": "spoof_identity",
                },
            }
        )
        return {
            "real_sender": real_agent,
            "spoofed_sender": spoofed_agent,
            "to": to_agent,
            "message": message,
            "response": (
                None if hook_result.action == "deny" else hook_result.message.get("content")
            ),
            "success": hook_result.action != "deny",
            "delivery_denied": hook_result.to_dict() if hook_result.action == "deny" else None,
            "detected": None,
        }

    def get_resource_usage(self, agent_name: str | None = None) -> dict[str, Any]:
        """Return process-local usage counters for the A3S adapter."""

        elapsed_time = time.time() - self._start_time
        if agent_name:
            return {
                "agent": agent_name,
                "api_calls": self._api_call_counts.get(agent_name, 0),
                "elapsed_time": elapsed_time,
                "process_id": os.getpid(),
            }
        return {
            "total_api_calls": sum(self._api_call_counts.values()),
            "elapsed_time": elapsed_time,
            "process_id": os.getpid(),
            "agents": {
                agent.name: {"api_calls": self._api_call_counts.get(agent.name, 0)}
                for agent in self.mas.get_agents()
            },
        }

"""Level 1: MAS Framework Layer - Base classes and data structures."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Compatibility re-export: the structured hook protocol is canonical in
# trinityguard.runtime.adapter_contract. Keep these names here so older Level 1
# imports remain stable while runtime/adapter code migrates to the canonical
# boundary.
from trinityguard.runtime.adapter_contract import (
    MessageDeliveryDeniedError,
    MessageHookResult,
    normalize_message_hook_result,
)


@dataclass
class AgentInfo:
    """Metadata about an agent in the MAS."""

    name: str
    role: str
    system_prompt: str | None = None
    tools: list[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Result from running a MAS workflow."""

    success: bool
    output: Any
    messages: list[dict]  # Full message history
    metadata: dict = field(default_factory=dict)
    error: str | None = None


class BaseMAS(ABC):
    """Abstract base class for MAS framework wrappers."""

    def __init__(self):
        self._message_hooks: list[Callable[[dict], dict | MessageHookResult]] = []

    @abstractmethod
    def get_agents(self) -> list[AgentInfo]:
        """Return list of all agents in the system.

        Returns:
            List of AgentInfo objects describing each agent
        """
        pass

    @abstractmethod
    def get_agent(self, name: str) -> Any:
        """Get a specific agent by name.

        Args:
            name: Agent name

        Returns:
            Framework-native agent object

        Raises:
            ValueError: If agent not found
        """
        pass

    @abstractmethod
    def run_workflow(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the MAS workflow with given task.

        This method should call registered message hooks during execution.

        Args:
            task: Task description
            **kwargs: Additional framework-specific parameters

        Returns:
            WorkflowResult with execution details
        """
        pass

    @abstractmethod
    def get_topology(self) -> dict:
        """Return the communication topology.

        Returns:
            Dict mapping agent names to lists of agents they can communicate with
        """
        pass

    def register_message_hook(self, hook: Callable[[dict], dict | MessageHookResult]):
        """Register a hook to intercept/modify messages during workflow execution.

        Hook signature: (message: dict) -> dict | MessageHookResult
        The hook receives a message dict and returns either a legacy modified
        message dict or a structured MessageHookResult. Structured results can
        explicitly deny delivery before the adapter sends the message.

        Args:
            hook: Callable that takes and returns a message dict
        """
        self._message_hooks.append(hook)

    def clear_message_hooks(self):
        """Clear all registered message hooks."""
        self._message_hooks.clear()

    def _apply_message_hooks_with_result(self, message: dict) -> MessageHookResult:
        """Apply hooks and preserve structured allow/replace/deny semantics."""

        final_result = MessageHookResult.allow(message)
        for hook in self._message_hooks:
            result = normalize_message_hook_result(hook(message))
            if result.action == "deny":
                return result
            message = result.message
            final_result = result
        return final_result

    def _apply_message_hooks(self, message: dict) -> dict:
        """Apply all registered hooks to a message.

        This should be called by subclasses during message processing.

        Args:
            message: Message dict to process

        Returns:
            Modified message dict
        """
        result = self._apply_message_hooks_with_result(message)
        if result.action == "deny":
            raise MessageDeliveryDeniedError(result)
        return result.message

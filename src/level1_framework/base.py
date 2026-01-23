"""Level 1: MAS Framework Layer - Base classes and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


@dataclass
class AgentInfo:
    """Metadata about an agent in the MAS."""
    name: str
    role: str
    system_prompt: Optional[str] = None
    tools: List[str] = field(default_factory=list)


@dataclass
class WorkflowResult:
    """Result from running a MAS workflow."""
    success: bool
    output: Any
    messages: List[Dict]  # Full message history
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


class BaseMAS(ABC):
    """Abstract base class for MAS framework wrappers."""

    def __init__(self):
        self._message_hooks: List[Callable[[Dict], Dict]] = []

    @abstractmethod
    def get_agents(self) -> List[AgentInfo]:
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
    def get_topology(self) -> Dict:
        """Return the communication topology.

        Returns:
            Dict mapping agent names to lists of agents they can communicate with
        """
        pass

    def register_message_hook(self, hook: Callable[[Dict], Dict]):
        """Register a hook to intercept/modify messages during workflow execution.

        Hook signature: (message: Dict) -> Dict
        The hook receives a message dict and returns a (potentially modified) message dict.

        Args:
            hook: Callable that takes and returns a message dict
        """
        self._message_hooks.append(hook)

    def clear_message_hooks(self):
        """Clear all registered message hooks."""
        self._message_hooks.clear()

    def _apply_message_hooks(self, message: Dict) -> Dict:
        """Apply all registered hooks to a message.

        This should be called by subclasses during message processing.

        Args:
            message: Message dict to process

        Returns:
            Modified message dict
        """
        for hook in self._message_hooks:
            message = hook(message)
        return message

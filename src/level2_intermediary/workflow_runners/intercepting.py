"""Intercepting WorkflowRunner implementation."""

from typing import List, Callable, Optional, Dict
from dataclasses import dataclass

from .base import WorkflowRunner
from ...level1_framework.base import WorkflowResult


@dataclass
class MessageInterception:
    """Configuration for intercepting/modifying messages."""
    source_agent: str
    target_agent: Optional[str]  # None = all targets
    modifier: Callable[[str], str]  # Function to modify message content
    condition: Optional[Callable[[Dict], bool]] = None  # When to apply


class InterceptingWorkflowRunner(WorkflowRunner):
    """Workflow execution with message interception/modification."""

    def __init__(self, mas, interceptions: List[MessageInterception]):
        """Initialize intercepting runner.

        Args:
            mas: Level 1 MAS instance
            interceptions: List of message interception rules
        """
        super().__init__(mas)
        self.interceptions = interceptions

    def run(self, task: str, **kwargs) -> WorkflowResult:
        """Execute workflow with message interception.

        Args:
            task: Task description
            **kwargs: Additional parameters

        Returns:
            WorkflowResult
        """
        # Register message hook with MAS
        self.mas.register_message_hook(self.on_message)

        try:
            # Apply pre-run hook
            task = self.pre_run_hook(task)

            # Execute workflow
            result = self.mas.run_workflow(task, **kwargs)

            # Apply post-run hook
            result = self.post_run_hook(result)

            return result
        finally:
            # Clean up hooks
            self.mas.clear_message_hooks()

    def on_message(self, message: Dict) -> Dict:
        """Intercept and potentially modify message.

        Args:
            message: Message dict

        Returns:
            Modified message dict
        """
        for interception in self.interceptions:
            if self._should_apply(interception, message):
                # Modify message content
                if "content" in message:
                    message["content"] = interception.modifier(message["content"])

        return message

    def _should_apply(self, interception: MessageInterception, message: Dict) -> bool:
        """Check if interception should be applied to message.

        Uses logical target (to) for matching, not physical target (physical_to).
        This ensures interception works correctly in GroupChat mode where messages
        are physically routed through chat_manager.

        Args:
            interception: Interception rule
            message: Message dict with 'from', 'to' (logical), and optionally 'physical_to'

        Returns:
            True if interception should be applied
        """
        # Check source agent
        if "from" in message and message["from"] != interception.source_agent:
            return False

        # Check target agent using logical target (to), not physical target
        if interception.target_agent is not None:
            logical_target = message.get("to")
            if logical_target and logical_target != interception.target_agent:
                return False

        # Check condition
        if interception.condition is not None:
            if not interception.condition(message):
                return False

        return True

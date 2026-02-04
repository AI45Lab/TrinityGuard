"""Combined Monitored + Intercepting WorkflowRunner implementation."""

from typing import Optional, Callable, List, Dict

from .monitored import MonitoredWorkflowRunner
from .intercepting import MessageInterception
from ..structured_logging import AgentStepLog


class MonitoredInterceptingRunner(MonitoredWorkflowRunner):
    """Combines monitoring and interception capabilities.

    This runner provides both:
    - Structured logging for runtime monitoring
    - Message interception/modification for testing
    """

    def __init__(self, mas, interceptions: List[MessageInterception],
                 stream_callback: Optional[Callable[[AgentStepLog], None]] = None):
        """Initialize combined runner.

        Args:
            mas: Level 1 MAS instance
            interceptions: List of message interception rules
            stream_callback: Optional callback for streaming log entries
        """
        super().__init__(mas, stream_callback)
        self.interceptions = interceptions

    def on_message(self, message: Dict) -> Dict:
        """Intercept message, then log it.

        Args:
            message: Message dict

        Returns:
            Modified message dict
        """
        # First, apply interceptions
        for interception in self.interceptions:
            if self._should_apply(interception, message):
                if "content" in message:
                    original_content = message["content"]
                    message["content"] = interception.modifier(message["content"])

                    # Log the interception
                    self.log_writer.log_agent_step(
                        agent_name="interceptor",
                        step_type="intercept",
                        content={
                            "original": original_content,
                            "modified": message["content"],
                            "source": interception.source_agent,
                            "target": interception.target_agent
                        }
                    )

        # Then, apply monitoring (call parent's on_message)
        return super().on_message(message)

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

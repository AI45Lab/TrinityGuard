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
                content = message.get("content")
                # Only intercept if there's actual content (not tool calls)
                if content is not None:
                    original_content = str(content) if content else ""
                    modified_content = interception.modifier(original_content)
                    message["content"] = modified_content

                    # Log the interception using dedicated method
                    self.log_writer.log_interception(
                        source_agent=message.get("from", "unknown"),
                        target_agent=interception.target_agent or message.get("to", "unknown"),
                        original_content=original_content,
                        modified_content=modified_content,
                        attack_type=getattr(interception, 'attack_type', None),
                        metadata={
                            "interception_source": interception.source_agent,
                            "interception_target": interception.target_agent
                        }
                    )

        # Then, apply monitoring (call parent's on_message)
        return super().on_message(message)

    def _should_apply(self, interception: MessageInterception, message: Dict) -> bool:
        """Check if interception should be applied to message.

        In GroupChat mode, messages are broadcast to all agents (to="broadcast"),
        so we only check the source_agent. The target_agent in interception config
        is used for logging purposes but not for matching in broadcast mode.

        Args:
            interception: Interception rule
            message: Message dict with 'from', 'to' (logical), and optionally 'physical_to'

        Returns:
            True if interception should be applied
        """
        # Check source agent - this is the primary matching criterion
        if "from" in message and message["from"] != interception.source_agent:
            return False

        # In GroupChat mode, 'to' is "broadcast", so we skip target check
        # when the message is broadcast (all agents receive it)
        logical_target = message.get("to")
        if interception.target_agent is not None:
            # Only check target if it's NOT a broadcast message (direct message mode)
            if logical_target and logical_target not in ("broadcast", "chat_manager"):
                if logical_target != interception.target_agent:
                    return False

        # Check condition
        if interception.condition is not None:
            if not interception.condition(message):
                return False

        return True

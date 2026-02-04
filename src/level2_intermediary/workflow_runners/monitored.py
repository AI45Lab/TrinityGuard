"""Monitored WorkflowRunner implementation."""

from typing import Optional, Callable, List, Dict
import uuid

from .base import WorkflowRunner
from ...level1_framework.base import WorkflowResult
from ..structured_logging import StructuredLogWriter, AgentStepLog


class MonitoredWorkflowRunner(WorkflowRunner):
    """Workflow execution with structured logging for runtime monitoring."""

    def __init__(self, mas, stream_callback: Optional[Callable[[AgentStepLog], None]] = None):
        """Initialize monitored runner.

        Args:
            mas: Level 1 MAS instance
            stream_callback: Optional callback for streaming log entries
        """
        super().__init__(mas)
        self.stream_callback = stream_callback
        self.log_writer = StructuredLogWriter()
        self.logs: List[AgentStepLog] = []

    def run(self, task: str, **kwargs) -> WorkflowResult:
        """Execute workflow with structured logging.

        Args:
            task: Task description
            **kwargs: Additional parameters including:
                - max_rounds: Maximum conversation rounds
                - silent: If True, suppress native framework output

        Returns:
            WorkflowResult with logs attached
        """
        # Start trace
        self.log_writer.start_trace(task)

        # Register message hook
        self.mas.register_message_hook(self.on_message)

        try:
            # Apply pre-run hook
            task = self.pre_run_hook(task)

            # Execute workflow (pass through kwargs including silent)
            result = self.mas.run_workflow(task, **kwargs)

            # End trace
            trace = self.log_writer.end_trace(success=result.success, error=result.error)

            # Store logs
            self.logs = trace.agent_steps

            # Attach logs to result
            result.metadata['trace'] = trace.to_dict()
            result.metadata['logs'] = [log.to_dict() for log in self.logs]

            # Apply post-run hook
            result = self.post_run_hook(result)

            return result

        except Exception as e:
            # End trace with error
            trace = self.log_writer.end_trace(success=False, error=str(e))
            self.logs = trace.agent_steps
            raise
        finally:
            # Clean up hooks
            self.mas.clear_message_hooks()

    def on_message(self, message: Dict) -> Dict:
        """Log message and call stream callback.

        Args:
            message: Message dict with fields:
                - from: Source agent name
                - to: Logical target agent name (for GroupChat, this is the actual recipient)
                - physical_to: Physical recipient (may be chat_manager in GroupChat mode)
                - content: Message content
                - tool_calls: Optional tool call information
                - tool_responses: Optional tool response information

        Returns:
            Unmodified message dict
        """
        # Extract message info
        from_agent = message.get("from", "unknown")
        to_agent = message.get("to", "unknown")
        physical_to = message.get("physical_to")
        content = message.get("content")
        tool_calls = message.get("tool_calls")
        tool_responses = message.get("tool_responses")
        function_call = message.get("function_call")

        # Determine message type
        if tool_calls:
            message_type = "tool_call"
            content_str = f"[Tool Call] {tool_calls}"
        elif tool_responses:
            message_type = "tool_response"
            content_str = str(content) if content else f"[Tool Response] {tool_responses}"
        elif function_call:
            message_type = "tool_call"
            content_str = f"[Function Call] {function_call}"
        elif content is None:
            message_type = "empty"
            content_str = "[No Content]"
        else:
            message_type = "text"
            content_str = str(content)

        # Log message
        message_id = str(uuid.uuid4())
        msg_metadata = {}
        if physical_to and physical_to != to_agent:
            msg_metadata["physical_to"] = physical_to
            msg_metadata["routing_mode"] = "group_chat"

        self.log_writer.log_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message=content_str,
            message_id=message_id,
            message_type=message_type,
            tool_calls=tool_calls,
            metadata=msg_metadata if msg_metadata else None
        )

        # Build metadata with routing info
        step_metadata = {
            "from": from_agent,
            "message_id": message_id,
            "message_type": message_type
        }
        if physical_to and physical_to != to_agent:
            step_metadata["physical_to"] = physical_to
            step_metadata["routing_mode"] = "group_chat"

        # Determine step type based on message type
        if message_type == "tool_call":
            step_type = "tool_call"
        elif message_type == "tool_response":
            step_type = "tool_response"
        else:
            step_type = "receive"

        # Log as agent step
        self.log_writer.log_agent_step(
            agent_name=to_agent,
            step_type=step_type,
            content=content_str,
            metadata=step_metadata
        )

        # Call stream callback if provided
        if self.stream_callback and self.log_writer.current_trace:
            logs = self.log_writer.get_current_logs()
            if logs:
                self.stream_callback(logs[-1])

        return message

    def get_logs(self) -> List[AgentStepLog]:
        """Get collected logs.

        Returns:
            List of AgentStepLog entries
        """
        return self.logs

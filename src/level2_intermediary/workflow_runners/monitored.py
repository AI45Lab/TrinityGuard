"""Monitored WorkflowRunner implementation."""

from typing import Optional, Callable, List
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
            **kwargs: Additional parameters

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

            # Execute workflow
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
            message: Message dict

        Returns:
            Unmodified message dict
        """
        # Extract message info
        from_agent = message.get("from", "unknown")
        to_agent = message.get("to", "unknown")
        content = message.get("content", "")

        # Log message
        message_id = str(uuid.uuid4())
        self.log_writer.log_message(
            from_agent=from_agent,
            to_agent=to_agent,
            message=content,
            message_id=message_id
        )

        # Log as agent step (receive)
        self.log_writer.log_agent_step(
            agent_name=to_agent,
            step_type="receive",
            content=content,
            metadata={"from": from_agent, "message_id": message_id}
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

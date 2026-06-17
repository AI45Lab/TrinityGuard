"""Structured log writer for Level 2 Intermediary."""

import json
import time
from pathlib import Path

from .schemas import AgentStepLog, InterceptionLog, MessageLog, WorkflowTrace


class StructuredLogWriter:
    """Writer for structured execution logs."""

    def __init__(self, output_file: str | None = None):
        """Initialize log writer.

        Args:
            output_file: Optional file path to write logs to
        """
        self.output_file = output_file
        self.current_trace: WorkflowTrace | None = None

    def start_trace(self, task: str) -> WorkflowTrace:
        """Start a new workflow trace.

        Args:
            task: Task description

        Returns:
            New WorkflowTrace instance
        """
        self.current_trace = WorkflowTrace(
            task=task,
            start_time=time.time()
        )
        return self.current_trace

    def log_agent_step(self, agent_name: str, step_type: str,
                       content: any, metadata: dict | None = None):
        """Log an agent step.

        Args:
            agent_name: Name of the agent
            step_type: Type of step (receive, think, tool_call, respond, error, intercept)
            content: Step content
            metadata: Optional metadata
        """
        if not self.current_trace:
            return

        step = AgentStepLog(
            timestamp=time.time(),
            agent_name=agent_name,
            step_type=step_type,
            content=content,
            metadata=metadata or {}
        )
        self.current_trace.agent_steps.append(step)

    def log_message(self, from_agent: str, to_agent: str,
                    message: str, message_id: str,
                    message_type: str = "text",
                    tool_calls: list | None = None,
                    metadata: dict | None = None):
        """Log an inter-agent message.

        Args:
            from_agent: Sender agent name
            to_agent: Receiver agent name
            message: Message content
            message_id: Unique message ID
            message_type: Type of message (text, tool_call, tool_response)
            tool_calls: Tool call details if message_type is tool_call
            metadata: Optional metadata
        """
        if not self.current_trace:
            return

        msg = MessageLog(
            timestamp=time.time(),
            from_agent=from_agent,
            to_agent=to_agent,
            message=message,
            message_id=message_id,
            message_type=message_type,
            tool_calls=tool_calls,
            metadata=metadata or {}
        )
        self.current_trace.messages.append(msg)

    def log_interception(self, source_agent: str, target_agent: str,
                         original_content: str, modified_content: str,
                         attack_type: str | None = None,
                         metadata: dict | None = None):
        """Log a message interception event.

        Args:
            source_agent: Original sender agent name
            target_agent: Target agent name
            original_content: Original message content before modification
            modified_content: Modified message content after interception
            attack_type: Type of attack being simulated
            metadata: Optional metadata
        """
        if not self.current_trace:
            return

        interception = InterceptionLog(
            timestamp=time.time(),
            source_agent=source_agent,
            target_agent=target_agent,
            original_content=original_content,
            modified_content=modified_content,
            attack_type=attack_type,
            metadata=metadata or {}
        )
        self.current_trace.interceptions.append(interception)

    def end_trace(self, success: bool = True, error: str | None = None) -> WorkflowTrace:
        """End the current workflow trace.

        Args:
            success: Whether workflow succeeded
            error: Optional error message

        Returns:
            Completed WorkflowTrace
        """
        if not self.current_trace:
            raise ValueError("No active trace to end")

        self.current_trace.end_time = time.time()
        self.current_trace.success = success
        self.current_trace.error = error

        # Write to file if configured
        if self.output_file:
            self._write_trace(self.current_trace)

        completed_trace = self.current_trace
        self.current_trace = None
        return completed_trace

    def _write_trace(self, trace: WorkflowTrace):
        """Write trace to file.

        Args:
            trace: WorkflowTrace to write
        """
        output_path = Path(self.output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(trace.to_dict(), default=str) + '\n')

    def get_current_logs(self) -> list[AgentStepLog]:
        """Get logs from current trace.

        Returns:
            List of AgentStepLog entries
        """
        if not self.current_trace:
            return []
        return self.current_trace.agent_steps

"""Level 2: MAS Intermediary base class."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum

from ..level1_framework.base import BaseMAS, WorkflowResult
from .workflow_runners import (
    WorkflowRunner,
    BasicWorkflowRunner,
    InterceptingWorkflowRunner,
    MonitoredWorkflowRunner,
    MonitoredInterceptingRunner,
    MessageInterception
)
from .structured_logging import AgentStepLog


class RunMode(Enum):
    """Workflow execution modes."""
    BASIC = "basic"
    INTERCEPTING = "intercepting"
    MONITORED = "monitored"
    MONITORED_INTERCEPTING = "monitored_intercepting"


class MASIntermediary(ABC):
    """Framework-agnostic interface for MAS safety operations."""

    def __init__(self, mas: BaseMAS):
        """Initialize intermediary.

        Args:
            mas: Level 1 MAS instance
        """
        self.mas = mas
        self._current_runner: Optional[WorkflowRunner] = None

    # === Pre-deployment Testing Scaffolding ===

    @abstractmethod
    def agent_chat(self, agent_name: str, message: str,
                   history: Optional[List] = None) -> str:
        """Direct point-to-point chat with an agent (for jailbreak testing).

        Args:
            agent_name: Name of agent to chat with
            message: Message to send
            history: Optional conversation history

        Returns:
            Agent's response
        """
        pass

    @abstractmethod
    def simulate_agent_message(self, from_agent: str, to_agent: str,
                               message: str) -> Dict:
        """Simulate a message from one agent to another (for interaction testing).

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            message: Message content

        Returns:
            Dict with response details
        """
        pass

    # === Workflow Execution ===

    def create_runner(self, mode: RunMode, **kwargs) -> WorkflowRunner:
        """Factory method to create appropriate WorkflowRunner.

        Args:
            mode: Execution mode (BASIC, INTERCEPTING, MONITORED, etc.)
            **kwargs: Mode-specific parameters
                - interceptions: List[MessageInterception] for INTERCEPTING modes
                - stream_callback: Callable for MONITORED modes

        Returns:
            Configured WorkflowRunner instance
        """
        if mode == RunMode.BASIC:
            return BasicWorkflowRunner(self.mas)

        elif mode == RunMode.INTERCEPTING:
            interceptions = kwargs.get('interceptions', [])
            return InterceptingWorkflowRunner(self.mas, interceptions)

        elif mode == RunMode.MONITORED:
            stream_callback = kwargs.get('stream_callback')
            return MonitoredWorkflowRunner(self.mas, stream_callback)

        elif mode == RunMode.MONITORED_INTERCEPTING:
            interceptions = kwargs.get('interceptions', [])
            stream_callback = kwargs.get('stream_callback')
            return MonitoredInterceptingRunner(self.mas, interceptions, stream_callback)

        else:
            raise ValueError(f"Unknown run mode: {mode}")

    def run_workflow(self, task: str, mode: RunMode = RunMode.BASIC, **kwargs) -> WorkflowResult:
        """Execute workflow with specified mode.

        Args:
            task: Task description
            mode: Execution mode
            **kwargs: Mode-specific parameters passed to create_runner

        Returns:
            WorkflowResult
        """
        runner = self.create_runner(mode, **kwargs)
        self._current_runner = runner
        try:
            result = runner.run(task, **kwargs)
            return result
        finally:
            self._current_runner = None

    def get_structured_logs(self) -> List[Dict]:
        """Get structured execution logs from last monitored run.

        Returns:
            List of log dicts
        """
        if isinstance(self._current_runner, MonitoredWorkflowRunner):
            return [log.to_dict() for log in self._current_runner.get_logs()]
        return []

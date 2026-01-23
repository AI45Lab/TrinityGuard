"""Base WorkflowRunner class for Level 2 Intermediary."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

from ...level1_framework.base import BaseMAS, WorkflowResult


class WorkflowRunner(ABC):
    """Base class for workflow execution strategies."""

    def __init__(self, mas: BaseMAS):
        """Initialize workflow runner.

        Args:
            mas: Level 1 MAS instance
        """
        self.mas = mas

    @abstractmethod
    def run(self, task: str, **kwargs) -> WorkflowResult:
        """Execute the workflow.

        Args:
            task: Task description
            **kwargs: Additional parameters

        Returns:
            WorkflowResult with execution details
        """
        pass

    def pre_run_hook(self, task: str) -> str:
        """Hook called before workflow execution.

        Override to modify task before execution.

        Args:
            task: Original task

        Returns:
            Modified task
        """
        return task

    def post_run_hook(self, result: WorkflowResult) -> WorkflowResult:
        """Hook called after workflow execution.

        Override to process result after execution.

        Args:
            result: Original result

        Returns:
            Modified result
        """
        return result

    def on_message(self, message: Dict) -> Dict:
        """Hook called for each message during execution.

        Override to intercept/modify messages.

        Args:
            message: Message dict

        Returns:
            Modified message dict
        """
        return message

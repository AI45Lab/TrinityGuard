"""Basic WorkflowRunner implementation."""

from .base import WorkflowRunner
from ...level1_framework.base import WorkflowResult


class BasicWorkflowRunner(WorkflowRunner):
    """Standard workflow execution without modifications."""

    def run(self, task: str, **kwargs) -> WorkflowResult:
        """Execute workflow without any modifications.

        Args:
            task: Task description
            **kwargs: Additional parameters

        Returns:
            WorkflowResult
        """
        # Apply pre-run hook
        task = self.pre_run_hook(task)

        # Execute workflow
        result = self.mas.run_workflow(task, **kwargs)

        # Apply post-run hook
        result = self.post_run_hook(result)

        return result

"""Level 2 workflow execution helpers for local orchestration paths."""

from __future__ import annotations

from typing import Any

from ..level1_framework.ag2.io_filter import suppress_ag2_tool_output
from ..level1_framework.base import WorkflowResult
from .base import MASIntermediary, RunMode


def run_with_suppressed_ag2_output(operation, *args: Any, **kwargs: Any):
    """Run an operation while suppressing framework-native AG2 console output."""

    with suppress_ag2_tool_output(suppress_all=True):
        return operation(*args, **kwargs)


def run_monitored_intermediary_workflow(
    intermediary: MASIntermediary,
    task: str,
    *,
    stream_callback=None,
    **kwargs: Any,
) -> WorkflowResult:
    """Run a legacy intermediary workflow in monitored mode with console noise suppressed.

    This helper preserves the Safety_MAS monitored fallback path
    without making Safety_MAS own the RunMode and AG2 output-suppression details.
    """

    return run_with_suppressed_ag2_output(
        intermediary.run_workflow,
        task,
        mode=RunMode.MONITORED,
        stream_callback=stream_callback,
        **kwargs,
    )

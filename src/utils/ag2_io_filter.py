"""AG2 IOStream filter to suppress verbose AG2 messages.

This module provides a custom IOStream implementation that filters out
AG2's verbose messages (EXECUTING FUNCTION, EXECUTED FUNCTION, TERMINATING RUN)
while preserving other output.
"""

from typing import Any, Callable
from contextlib import contextmanager

try:
    from autogen.io.base import IOStream
    from autogen.io.console import IOConsole
    from autogen.events.base_event import BaseEvent
    from autogen.events.agent_events import (
        ExecuteFunctionEvent,
        ExecutedFunctionEvent,
        TerminationEvent
    )
except ImportError:
    try:
        from pyautogen.io.base import IOStream
        from pyautogen.io.console import IOConsole
        from pyautogen.events.base_event import BaseEvent
        from pyautogen.events.agent_events import (
            ExecuteFunctionEvent,
            ExecutedFunctionEvent,
            TerminationEvent
        )
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")


class FilteredIOConsole(IOConsole):
    """IOConsole that filters out verbose AG2 messages.

    This class extends IOConsole to suppress the verbose messages that AG2
    prints during workflow execution, including:
    - EXECUTING FUNCTION / EXECUTED FUNCTION messages
    - TERMINATING RUN messages
    """

    def __init__(self, filter_tool_messages: bool = True,
                 filter_termination_messages: bool = True):
        """Initialize filtered console.

        Args:
            filter_tool_messages: If True, suppress tool execution messages
            filter_termination_messages: If True, suppress termination messages
        """
        super().__init__()
        self.filter_tool_messages = filter_tool_messages
        self.filter_termination_messages = filter_termination_messages

    def send(self, message: BaseEvent) -> None:
        """Send a message to the output stream, filtering verbose messages.

        Args:
            message: The message event to send
        """
        # Filter out tool execution messages if enabled
        if self.filter_tool_messages:
            if isinstance(message, (ExecuteFunctionEvent, ExecutedFunctionEvent)):
                return  # Suppress tool execution messages

        # Filter out termination messages if enabled
        if self.filter_termination_messages:
            if isinstance(message, TerminationEvent):
                return  # Suppress termination messages

        # Call parent's send for other messages
        super().send(message)


@contextmanager
def suppress_ag2_tool_output():
    """Context manager to suppress AG2 tool execution output.

    Usage:
        with suppress_ag2_tool_output():
            # AG2 code that calls tools
            result = mas.run_workflow(task)

    This temporarily replaces the global IOStream with a filtered version
    that suppresses EXECUTING/EXECUTED FUNCTION messages.
    """
    # Create filtered console
    filtered_console = FilteredIOConsole(filter_tool_messages=True)

    # Save original global default
    try:
        original_default = IOStream.get_global_default()
    except RuntimeError:
        original_default = None

    try:
        # Set filtered console as global default
        IOStream.set_global_default(filtered_console)
        yield
    finally:
        # Restore original default
        if original_default is not None:
            IOStream.set_global_default(original_default)

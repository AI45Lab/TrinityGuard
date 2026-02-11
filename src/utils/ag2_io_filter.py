"""AG2 IOStream filter to suppress verbose AG2 messages.

This module provides a custom IOStream implementation that filters out
AG2's verbose messages (EXECUTING FUNCTION, EXECUTED FUNCTION, TERMINATING RUN)
while preserving other output.

AG2 uses two output mechanisms:
1. IOStream.send() for event-based output
2. logging.Logger ('ag2.event.processor') for event_print() output

This module handles both mechanisms to fully suppress verbose output.
"""

import logging
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
    - Option to suppress ALL messages
    """

    def __init__(self, filter_tool_messages: bool = True,
                 filter_termination_messages: bool = True,
                 suppress_all: bool = False):
        """Initialize filtered console.

        Args:
            filter_tool_messages: If True, suppress tool execution messages
            filter_termination_messages: If True, suppress termination messages
            suppress_all: If True, suppress ALL output
        """
        super().__init__()
        self.filter_tool_messages = filter_tool_messages
        self.filter_termination_messages = filter_termination_messages
        self.suppress_all = suppress_all

    def send(self, message: BaseEvent) -> None:
        """Send a message to the output stream, filtering verbose messages.

        Args:
            message: The message event to send
        """
        # If universal suppression is enabled, return immediately
        if self.suppress_all:
            return

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


# AG2 event logger name (from autogen.logger.logger_utils)
_AG2_EVENT_LOGGER_NAME = "ag2.event.processor"


class AG2EventFilter(logging.Filter):
    """Logging filter to suppress AG2 tool execution messages.

    This filter blocks log messages containing EXECUTING FUNCTION or
    EXECUTED FUNCTION patterns from the ag2.event.processor logger.
    """

    def __init__(self, suppress_all: bool = False):
        super().__init__()
        self.suppress_all = suppress_all

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out tool execution messages.

        Args:
            record: The log record to filter

        Returns:
            False to suppress the message, True to allow it
        """
        if self.suppress_all:
            return False

        msg = record.getMessage()
        # Suppress tool execution messages
        if ">>>>>>>> EXECUTING FUNCTION" in msg:
            return False
        if ">>>>>>>> EXECUTED FUNCTION" in msg:
            return False
        # Suppress termination messages
        if ">>>>>>>> TERMINATING RUN" in msg:
            return False
        return True


@contextmanager
def suppress_ag2_tool_output(debug: bool = False, suppress_all: bool = False):
    """Context manager to suppress AG2 tool execution output.

    Usage:
        with suppress_ag2_tool_output(suppress_all=True):
            # AG2 code that calls tools
            result = mas.run_workflow(task)

    This suppresses EXECUTING/EXECUTED FUNCTION messages by:
    1. Setting filtered IOStream as both global and context-local default
    2. Adding a filter to the ag2.event.processor logger

    Note: AG2 uses IOStream.get_default() which checks context-local default first,
    then falls back to global default. We must set both to ensure filtering works.

    Args:
        debug: If True, print debug information about IOStream state
        suppress_all: If True, suppress ALL AG2 output (chat messages, etc.)
    """
    # Check existing default for inheritance
    try:
        current_default = IOStream.get_default()
        if isinstance(current_default, FilteredIOConsole):
            suppress_all = suppress_all or current_default.suppress_all
    except (RuntimeError, ImportError):
        current_default = None

    # Create filtered console for IOStream
    filtered_console = FilteredIOConsole(
        filter_tool_messages=True,
        suppress_all=suppress_all
    )

    # Save original global default
    try:
        original_global = IOStream.get_global_default()
    except RuntimeError:
        original_global = None

    # Create and add filter to AG2 event logger
    event_filter = AG2EventFilter(suppress_all=suppress_all)
    ag2_logger = logging.getLogger(_AG2_EVENT_LOGGER_NAME)
    ag2_logger.addFilter(event_filter)

    if debug:
        print(f"[DEBUG] suppress_ag2_tool_output: entering context (suppress_all={suppress_all})")
        print(f"[DEBUG] original_global: {type(original_global).__name__ if original_global else None}")
        print(f"[DEBUG] filtered_console: {type(filtered_console).__name__}")

    try:
        # Set filtered console as global default
        IOStream.set_global_default(filtered_console)
        # Also set as context-local default using the context manager
        # This ensures AG2's get_default() returns our filtered console
        with IOStream.set_default(filtered_console):
            if debug:
                current = IOStream.get_default()
                print(f"[DEBUG] inside context - IOStream.get_default(): {type(current).__name__}")
            yield
    finally:
        # Restore original global default
        if original_global is not None:
            IOStream.set_global_default(original_global)
        # Remove the filter from logger
        ag2_logger.removeFilter(event_filter)
        if debug:
            print(f"[DEBUG] suppress_ag2_tool_output: exiting context")
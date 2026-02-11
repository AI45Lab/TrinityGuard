"""AG2 IOStream filter to suppress verbose AG2 messages.

This module provides a simple way to suppress AG2's verbose messages
by filtering logging output.

Note: Event-based filtering (IOStream) has been removed or changed
in newer AG2 versions. This module now focuses on logging-based filtering.
"""

import logging
from contextlib import contextmanager

# ============================================================================
# Logging Filter
# ============================================================================

class AG2EventFilter(logging.Filter):
    """Logging filter to suppress AG2 tool execution messages.

    This filter blocks log messages containing EXECUTING FUNCTION or
    EXECUTED FUNCTION patterns from AG2 loggers.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter out tool execution messages.

        Args:
            record: The log record to filter

        Returns:
            False to suppress the message, True to allow it
        """
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
def suppress_ag2_tool_output(debug: bool = False):
    """Context manager to suppress AG2 tool execution output.

    This works by adding a filter to AG2's loggers.

    Usage:
        with suppress_ag2_tool_output():
            # AG2 code that calls tools
            result = mas.run_workflow(task)

    Args:
        debug: If True, print debug information

    Note: In newer AG2 versions, IOStream-based filtering may not work.
    We use logging-based filtering instead.
    """
    # Create and add filter to AG2 event logger
    event_filter = AG2EventFilter()

    # AG2 uses multiple logger names, try to filter common ones
    logger_names = [
        "ag2.event.processor",  # AG2 event logger
        "autogen.agentchat",      # Agent chat logger
        "autogen.oai.client",      # OpenAI client logger
    ]

    loggers_with_filter = []
    for logger_name in logger_names:
        try:
            ag2_logger = logging.getLogger(logger_name)
            ag2_logger.addFilter(event_filter)
            loggers_with_filter.append(logger_name)
            if debug:
                print(f"[DEBUG] Added filter to logger: {logger_name}")
        except Exception as e:
            if debug:
                print(f"[DEBUG] Failed to add filter to {logger_name}: {e}")

    try:
        if debug:
            print(f"[DEBUG] suppress_ag2_tool_output: entering context")
            print(f"[DEBUG] Filtered loggers: {loggers_with_filter}")

        yield

    finally:
        # Remove filters from loggers
        for logger_name in loggers_with_filter:
            try:
                ag2_logger = logging.getLogger(logger_name)
                ag2_logger.removeFilter(event_filter)
                if debug:
                    print(f"[DEBUG] Removed filter from logger: {logger_name}")
            except Exception:
                pass

        if debug:
            print(f"[DEBUG] suppress_ag2_tool_output: exiting context")

"""Level 3: Safety_MAS Layer."""

# Use try-except to allow submodules to be imported independently
try:
    from .safety_mas import Safety_MAS, MonitorSelectionMode
    from .risk_tests import BaseRiskTest, TestCase, TestResult
    from .monitor_agents import BaseMonitorAgent, Alert
    from .console_logger import Level3ConsoleLogger, get_console_logger, WorkflowSession

    __all__ = [
        "Safety_MAS",
        "MonitorSelectionMode",
        "BaseRiskTest",
        "TestCase",
        "TestResult",
        "BaseMonitorAgent",
        "Alert",
        "Level3ConsoleLogger",
        "get_console_logger",
        "WorkflowSession",
    ]
except ImportError:
    # Allow submodules like jailbreak_frameworks to be imported independently
    __all__ = []

"""Custom exceptions for MASSafetyGuard."""


class MASSafetyError(Exception):
    """Base exception for MASSafetyGuard."""
    pass


class MASFrameworkError(MASSafetyError):
    """Errors from Level 1 MAS framework."""
    pass


class IntermediaryError(MASSafetyError):
    """Errors from Level 2 intermediary operations."""
    pass


class RiskTestError(MASSafetyError):
    """Errors during risk testing."""
    pass


class MonitorError(MASSafetyError):
    """Errors from monitor agents."""
    pass


class ConfigurationError(MASSafetyError):
    """Errors in configuration."""
    pass


class LLMError(MASSafetyError):
    """Errors from LLM API calls."""
    pass

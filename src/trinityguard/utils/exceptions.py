"""Custom exceptions for TrinityGuard."""


class TrinitySafetyError(Exception):
    """Base exception for TrinityGuard."""
    pass


class MASFrameworkError(TrinitySafetyError):
    """Errors from Level 1 MAS framework."""
    pass


class IntermediaryError(TrinitySafetyError):
    """Errors from Level 2 intermediary operations."""
    pass


class RiskTestError(TrinitySafetyError):
    """Errors during risk testing."""
    pass


class MonitorError(TrinitySafetyError):
    """Errors from monitor agents."""
    pass


class ConfigurationError(TrinitySafetyError):
    """Errors in configuration."""
    pass


class LLMError(TrinitySafetyError):
    """Errors from LLM API calls."""
    pass

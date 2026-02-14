"""Utility modules for TrinityGuard."""

from .exceptions import (
    TrinitySafetyError,
    MASFrameworkError,
    IntermediaryError,
    RiskTestError,
    MonitorError,
    ConfigurationError,
    LLMError,
)
from .config import (
    TrinitySafetyConfig,
    LLMConfig,
    LoggingConfig,
    TestingConfig,
    MonitoringConfig,
    get_config,
    set_config,
    load_config,
)
from .llm_client import (
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    get_llm_client,
    get_monitor_llm_client,
)
from .llm_config import (
    LLMConfig as LLMConfigNew,
    MASLLMConfig,
    MonitorLLMConfig,
    ConfigNotFoundError,
    load_llm_config,
    get_llm_config,
    reset_llm_config,
    load_mas_llm_config,
    get_mas_llm_config,
    reset_mas_llm_config,
    load_monitor_llm_config,
    get_monitor_llm_config,
    reset_monitor_llm_config,
)
from .logging_config import (
    StructuredLogger,
    get_logger,
)

__all__ = [
    # Exceptions
    "TrinitySafetyError",
    "MASFrameworkError",
    "IntermediaryError",
    "RiskTestError",
    "MonitorError",
    "ConfigurationError",
    "LLMError",
    # Config
    "TrinitySafetyConfig",
    "LLMConfig",
    "LoggingConfig",
    "TestingConfig",
    "MonitoringConfig",
    "get_config",
    "set_config",
    "load_config",
    # LLM Config (new)
    "MASLLMConfig",
    "MonitorLLMConfig",
    "ConfigNotFoundError",
    "load_llm_config",
    "get_llm_config",
    "reset_llm_config",
    "load_mas_llm_config",
    "get_mas_llm_config",
    "reset_mas_llm_config",
    "load_monitor_llm_config",
    "get_monitor_llm_config",
    "reset_monitor_llm_config",
    # LLM Client
    "BaseLLMClient",
    "OpenAIClient",
    "AnthropicClient",
    "get_llm_client",
    "get_monitor_llm_client",
    # Logging
    "StructuredLogger",
    "get_logger",
]

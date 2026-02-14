"""LLM configuration loader for TrinityGuard."""

import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from .exceptions import ConfigurationError


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096

    def get_api_key(self) -> str:
        """Get API key, prioritizing direct config over environment variable."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                return key
        raise ConfigurationError(
            "No API key configured. Set 'api_key' in llm_config.yaml "
            "or set the environment variable specified in 'api_key_env'."
        )

    def to_ag2_config(self) -> dict:
        """Convert to AG2/AutoGen llm_config format."""
        config = {
            "model": self.model,
            "api_key": self.get_api_key(),
            "temperature": self.temperature,
        }
        if self.base_url:
            config["base_url"] = self.base_url
        return config


class ConfigNotFoundError(Exception):
    """Configuration file not found error."""
    pass


@dataclass
class MASLLMConfig:
    """LLM configuration for tested MAS (Multi-Agent System)."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096

    def get_api_key(self) -> str:
        """Get API key, prioritizing direct config over environment variable."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                return key
        raise ConfigurationError(
            "No API key configured. Set 'api_key' in mas_llm_config.yaml "
            "or set the environment variable specified in 'api_key_env'."
        )

    def to_ag2_config(self) -> dict:
        """Convert to AG2/AutoGen llm_config format."""
        config = {
            "model": self.model,
            "api_key": self.get_api_key(),
            "temperature": self.temperature,
        }
        if self.base_url:
            config["base_url"] = self.base_url
        return config


@dataclass
class MonitorLLMConfig:
    """LLM configuration for Monitor agents and Judges (with extended settings)."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096

    # Extended settings for monitors/judges
    judge_temperature: float = 0.1
    judge_max_tokens: int = 500
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout: int = 30

    def get_api_key(self) -> str:
        """Get API key, prioritizing direct config over environment variable."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                return key
        raise ConfigurationError(
            "No API key configured. Set 'api_key' in monitor_llm_config.yaml "
            "or set the environment variable specified in 'api_key_env'."
        )


# Global config instance
_llm_config: Optional[LLMConfig] = None

# Global config instances
_mas_llm_config: Optional[MASLLMConfig] = None
_monitor_llm_config: Optional[MonitorLLMConfig] = None


def load_mas_llm_config(path: Optional[str] = None) -> MASLLMConfig:
    """Load MAS LLM configuration from YAML file."""
    global _mas_llm_config

    if path is None:
        path = Path(__file__).parent.parent.parent / "config" / "mas_llm_config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        raise ConfigNotFoundError(
            f"MAS LLM config file not found: {path}\n"
            f"Please create the config file with the following format:\n"
            f"  provider: openai\n"
            f"  model: gpt-4o-mini\n"
            f"  api_key: your-api-key\n"
            f"  base_url: your-base-url  # optional\n"
            f"  temperature: 0\n"
            f"  max_tokens: 4096"
        )

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    _mas_llm_config = MASLLMConfig(
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key"),
        api_key_env=data.get("api_key_env"),
        base_url=data.get("base_url"),
        temperature=data.get("temperature", 0),
        max_tokens=data.get("max_tokens", 4096),
    )

    return _mas_llm_config


def get_mas_llm_config() -> MASLLMConfig:
    """Get the MAS LLM configuration, loading if necessary."""
    global _mas_llm_config
    if _mas_llm_config is None:
        _mas_llm_config = load_mas_llm_config()
    return _mas_llm_config


def load_monitor_llm_config(path: Optional[str] = None) -> MonitorLLMConfig:
    """Load Monitor LLM configuration from YAML file."""
    global _monitor_llm_config

    if path is None:
        path = Path(__file__).parent.parent.parent / "config" / "monitor_llm_config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        raise ConfigNotFoundError(
            f"Monitor LLM config file not found: {path}\n"
            f"Please create the config file with the following format:\n"
            f"  provider: openai\n"
            f"  model: gpt-4o-mini\n"
            f"  api_key: your-api-key\n"
            f"  base_url: your-base-url  # optional\n"
            f"  temperature: 0\n"
            f"  max_tokens: 4096\n"
            f"  judge_temperature: 0.1\n"
            f"  judge_max_tokens: 500\n"
            f"  retry_count: 3\n"
            f"  retry_delay: 1.0\n"
            f"  timeout: 30"
        )

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    _monitor_llm_config = MonitorLLMConfig(
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key"),
        api_key_env=data.get("api_key_env"),
        base_url=data.get("base_url"),
        temperature=data.get("temperature", 0),
        max_tokens=data.get("max_tokens", 4096),
        judge_temperature=data.get("judge_temperature", 0.1),
        judge_max_tokens=data.get("judge_max_tokens", 500),
        retry_count=data.get("retry_count", 3),
        retry_delay=data.get("retry_delay", 1.0),
        timeout=data.get("timeout", 30),
    )

    return _monitor_llm_config


def get_monitor_llm_config() -> MonitorLLMConfig:
    """Get the Monitor LLM configuration, loading if necessary."""
    global _monitor_llm_config
    if _monitor_llm_config is None:
        _monitor_llm_config = load_monitor_llm_config()
    return _monitor_llm_config


def reset_mas_llm_config():
    """Reset the global MAS LLM config (useful for testing)."""
    global _mas_llm_config
    _mas_llm_config = None


def reset_monitor_llm_config():
    """Reset the global Monitor LLM config (useful for testing)."""
    global _monitor_llm_config
    _monitor_llm_config = None


def load_llm_config(path: Optional[str] = None) -> LLMConfig:
    """DEPRECATED: Use load_mas_llm_config() or load_monitor_llm_config() instead."""
    warnings.warn(
        "load_llm_config() is deprecated. Use load_mas_llm_config() for MAS "
        "or load_monitor_llm_config() for monitors.",
        DeprecationWarning,
        stacklevel=2
    )
    mas_config = load_mas_llm_config(path)
    return LLMConfig(
        provider=mas_config.provider,
        model=mas_config.model,
        api_key=mas_config.api_key,
        api_key_env=mas_config.api_key_env,
        base_url=mas_config.base_url,
        temperature=mas_config.temperature,
        max_tokens=mas_config.max_tokens,
    )


def get_llm_config() -> LLMConfig:
    """DEPRECATED: Use get_mas_llm_config() or get_monitor_llm_config() instead."""
    warnings.warn(
        "get_llm_config() is deprecated. Use get_mas_llm_config() for MAS "
        "or get_monitor_llm_config() for monitors.",
        DeprecationWarning,
        stacklevel=2
    )
    mas_config = get_mas_llm_config()
    return LLMConfig(
        provider=mas_config.provider,
        model=mas_config.model,
        api_key=mas_config.api_key,
        api_key_env=mas_config.api_key_env,
        base_url=mas_config.base_url,
        temperature=mas_config.temperature,
        max_tokens=mas_config.max_tokens,
    )


def reset_llm_config():
    """DEPRECATED: Use reset_mas_llm_config() or reset_monitor_llm_config() instead."""
    warnings.warn(
        "reset_llm_config() is deprecated. Use reset_mas_llm_config() "
        "or reset_monitor_llm_config() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    reset_mas_llm_config()
    reset_monitor_llm_config()

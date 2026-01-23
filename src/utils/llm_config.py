"""LLM configuration loader for MASSafetyGuard."""

import os
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


# Global config instance
_llm_config: Optional[LLMConfig] = None


def load_llm_config(path: Optional[str] = None) -> LLMConfig:
    """Load LLM configuration from YAML file.

    Args:
        path: Optional path to config file. Defaults to config/llm_config.yaml

    Returns:
        LLMConfig instance
    """
    global _llm_config

    if path is None:
        # Default path relative to project root
        path = Path(__file__).parent.parent.parent / "config" / "llm_config.yaml"
    else:
        path = Path(path)

    if not path.exists():
        raise ConfigurationError(f"LLM config file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    _llm_config = LLMConfig(
        provider=data.get("provider", "openai"),
        model=data.get("model", "gpt-4o-mini"),
        api_key=data.get("api_key"),
        api_key_env=data.get("api_key_env"),
        base_url=data.get("base_url"),
        temperature=data.get("temperature", 0),
        max_tokens=data.get("max_tokens", 4096),
    )

    return _llm_config


def get_llm_config() -> LLMConfig:
    """Get the current LLM configuration, loading if necessary."""
    global _llm_config
    if _llm_config is None:
        _llm_config = load_llm_config()
    return _llm_config


def reset_llm_config():
    """Reset the global LLM config (useful for testing)."""
    global _llm_config
    _llm_config = None

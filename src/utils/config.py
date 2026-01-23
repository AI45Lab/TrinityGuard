"""Configuration management for MASSafetyGuard."""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path

import yaml

from .exceptions import ConfigurationError


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key_env: str = "MASSAFETY_LLM_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 4096

    @property
    def api_key(self) -> Optional[str]:
        """Get API key from environment."""
        return os.getenv(self.api_key_env)


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "massafety.log"
    format: str = "json"
    console_output: bool = True


@dataclass
class TestingConfig:
    """Testing configuration."""
    timeout: int = 300
    parallel: bool = False
    use_dynamic_cases: bool = False
    max_retries: int = 3


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    buffer_size: int = 1000
    alert_threshold: int = 3
    stream_interval: float = 0.1


@dataclass
class MASSafetyConfig:
    """Main configuration class."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    risk_tests_enabled: List[str] = field(default_factory=list)
    monitor_agents_enabled: List[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str) -> 'MASSafetyConfig':
        """Load configuration from YAML file."""
        path = Path(path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return cls._from_dict(data)

    @classmethod
    def from_env(cls) -> 'MASSafetyConfig':
        """Load configuration from environment variables."""
        config = cls()

        # Override with environment variables if present
        if os.getenv('MASSAFETY_LLM_PROVIDER'):
            config.llm.provider = os.getenv('MASSAFETY_LLM_PROVIDER')
        if os.getenv('MASSAFETY_LLM_MODEL'):
            config.llm.model = os.getenv('MASSAFETY_LLM_MODEL')
        if os.getenv('MASSAFETY_LOG_LEVEL'):
            config.logging.level = os.getenv('MASSAFETY_LOG_LEVEL')

        return config

    @classmethod
    def _from_dict(cls, data: dict) -> 'MASSafetyConfig':
        """Create config from dictionary."""
        llm_data = data.get('llm', {})
        logging_data = data.get('logging', {})
        testing_data = data.get('testing', )
        monitoring_data = data.get('monitoring', {})

        return cls(
            llm=LLMConfig(**llm_data),
            logging=LoggingConfig(**logging_data),
            testing=TestingConfig(**testing_data),
            monitoring=MonitoringConfig(**monitoring_data),
            risk_tests_enabled=data.get('risk_tests', {}).get('enabled', []),
            monitor_agents_enabled=data.get('monitor_agents', ).get('enabled', []),
        )

    @classmethod
    def default(cls) -> 'MASSafetyConfig':
        """Get default configuration."""
        default_path = Path(__file__).parent.parent.parent / 'config' / 'default.yaml'
        if default_path.exists():
            return cls.from_yaml(str(default_path))
        return cls()


# Global config instance
_config: Optional[MASSafetyConfig] = None


def get_config() -> MASSafetyConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = MASSafetyConfig.default()
    return _config


def set_config(config: MASSafetyConfig):
    """Set global configuration instance."""
    global _config
    _config = config


def load_config(path: str):
    """Load configuration from file and set as global."""
    global _config
    _config = MASSafetyConfig.from_yaml(path)

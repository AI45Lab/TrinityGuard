"""统一配置加载模块。

只负责 logging、testing、monitoring 等非 LLM 配置。
LLM 配置由 llm_config.py 独立管理。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class LoggingConfig:
    level: str = "INFO"
    test_log_dir: str = "logs/tests"


@dataclass
class TestingConfig:
    timeout: int = 300
    use_dynamic_cases: bool = False
    consensus_n: int = 3


@dataclass
class TrinityGuardConfig:
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    testing: TestingConfig = field(default_factory=TestingConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> TrinityGuardConfig:
        """从 YAML 文件加载配置。"""
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        logging_data = data.get("logging", {})
        testing_data = data.get("testing", {})

        return cls(
            logging=LoggingConfig(**{
                k: v for k, v in logging_data.items()
                if k in LoggingConfig.__dataclass_fields__
            }),
            testing=TestingConfig(**{
                k: v for k, v in testing_data.items()
                if k in TestingConfig.__dataclass_fields__
            }),
        )


_config: TrinityGuardConfig | None = None


def get_config() -> TrinityGuardConfig:
    """获取全局配置（懒加载）。"""
    global _config
    if _config is None:
        config_path = os.environ.get(
            "TRINITYGUARD_CONFIG",
            "config/default.yaml",
        )
        _config = TrinityGuardConfig.from_yaml(config_path)
    return _config


def reset_config() -> None:
    """重置全局配置（用于测试）。"""
    global _config
    _config = None

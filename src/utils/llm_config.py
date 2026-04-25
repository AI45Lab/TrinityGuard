"""LLM configuration loader — 支持多 profile 和按 agent/monitor 单独配置."""

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List
import yaml
from .exceptions import ConfigurationError


@dataclass
class LLMProfile:
    """单个 LLM 配置 profile."""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096
    timeout: int = 30
    price: List[float] = field(default_factory=list)

    def get_api_key(self) -> str:
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                return key
        raise ConfigurationError(
            f"No API key configured for provider '{self.provider}'. "
            f"Set api_key directly or set the env var in api_key_env."
        )

    def to_ag2_config(self) -> dict:
        """转换为 AG2/AutoGen llm_config 格式."""
        config = {
            "model": self.model,
            "api_key": self.get_api_key(),
            "temperature": self.temperature,
        }
        if self.base_url:
            config["base_url"] = self.base_url
        elif self.provider == "deepseek":
            config["base_url"] = "https://api.deepseek.com/v1"

        # ⭐ 修复：独立判断 price，而不是 elif
        if self.price:
            config["price"] = self.price
        print(f"LLMProfile.to_ag2_config() generated config: {config}")
        return config


@dataclass
class MASLLMConfig:
    """MAS 多 agent LLM 配置容器."""
    default_profile: LLMProfile = field(default_factory=LLMProfile)
    agent_profiles: Dict[str, LLMProfile] = field(default_factory=dict)

    def get_profile_for_agent(self, agent_name: str) -> LLMProfile:
        """获取指定 agent 的 LLM profile，找不到则用 default."""
        return self.agent_profiles.get(agent_name, self.default_profile)

    # 向后兼容：让旧代码 get_mas_llm_config().model 等仍然可用
    @property
    def provider(self) -> str:
        return self.default_profile.provider

    @property
    def model(self) -> str:
        return self.default_profile.model

    @property
    def base_url(self) -> Optional[str]:
        return self.default_profile.base_url

    @property
    def temperature(self) -> float:
        return self.default_profile.temperature

    @property
    def max_tokens(self) -> int:
        return self.default_profile.max_tokens

    def get_api_key(self) -> str:
        return self.default_profile.get_api_key()

    def to_ag2_config(self) -> dict:
        return self.default_profile.to_ag2_config()


@dataclass
class MonitorLLMConfig:
    """Monitor/Judge 多 monitor LLM 配置容器."""
    default_profile: LLMProfile = field(default_factory=LLMProfile)
    monitor_profiles: Dict[str, LLMProfile] = field(default_factory=dict)

    # Judge 专属参数
    judge_temperature: float = 0.1
    judge_max_tokens: int = 8000
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout: int = 30

    def get_profile_for_monitor(self, monitor_name: str) -> LLMProfile:
        """获取指定 monitor 的 LLM profile，找不到则用 default."""
        return self.monitor_profiles.get(monitor_name, self.default_profile)

    # 向后兼容属性
    @property
    def provider(self) -> str:
        return self.default_profile.provider

    @property
    def model(self) -> str:
        return self.default_profile.model

    @property
    def base_url(self) -> Optional[str]:
        return self.default_profile.base_url

    @property
    def temperature(self) -> float:
        return self.default_profile.temperature

    @property
    def max_tokens(self) -> int:
        return self.default_profile.max_tokens

    def get_api_key(self) -> str:
        return self.default_profile.get_api_key()


# ─── 内部工具函数 ──────────────────────────────────────────

def _load_profiles(config_dir: Path) -> Dict[str, LLMProfile]:
    """加载 llm_profiles.yaml 中定义的所有 profile."""
    profiles_path = config_dir / "llm_profiles.yaml"
    if not profiles_path.exists():
        return {}

    with open(profiles_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    profiles = {}
    for name, cfg in data.get("profiles", {}).items():
        profiles[name] = LLMProfile(
            provider=cfg.get("provider", "openai"),
            model=cfg.get("model", "gpt-4o-mini"),
            api_key=cfg.get("api_key"),
            api_key_env=cfg.get("api_key_env"),
            base_url=cfg.get("base_url"),
            temperature=cfg.get("temperature", 0),
            max_tokens=cfg.get("max_tokens", 4096),
            timeout=cfg.get("timeout", 30),
            price=cfg.get("price", [0.00028, 0.00028])
        )
    return profiles


def _resolve_profile(cfg_block: dict, named_profiles: Dict[str, LLMProfile]) -> LLMProfile:
    """
    将 yaml 配置块解析为 LLMProfile。
    支持两种写法：
      1. { profile: "deepseek_r1" }            # 引用命名 profile
      2. { provider: "deepseek", model: ... }  # 直接内联配置
    """
    if "profile" in cfg_block:
        profile_name = cfg_block["profile"]
        if profile_name not in named_profiles:
            raise ConfigurationError(
                f"Profile '{profile_name}' not found in llm_profiles.yaml. "
                f"Available: {list(named_profiles.keys())}"
            )
        base = named_profiles[profile_name]
        # 允许在引用 profile 基础上覆盖部分字段
        overrides = {k: v for k, v in cfg_block.items() if k != "profile"}
        if overrides:
            import dataclasses
            # Only pass overrides that are valid fields for LLMProfile
            profile_fields = {f.name for f in dataclasses.fields(base)}
            valid_overrides = {k: v for k, v in overrides.items() if k in profile_fields}
            invalid_keys = [k for k in overrides.keys() if k not in profile_fields]
            if invalid_keys:
                # Warn that some override keys were ignored (e.g., judge_temperature)
                warnings.warn(f"Ignored profile override keys not present in LLMProfile: {invalid_keys}")
            if valid_overrides:
                return dataclasses.replace(base, **valid_overrides)
        # No overrides or no valid overrides — return base profile unchanged
        return base
    else:
        print("Warning: No 'profile' key found in config block. Interpreting as inline LLMProfile config.")
        return LLMProfile(
            provider=cfg_block.get("provider", "openai"),
            model=cfg_block.get("model", "gpt-4o-mini"),
            api_key=cfg_block.get("api_key"),
            api_key_env=cfg_block.get("api_key_env"),
            base_url=cfg_block.get("base_url"),
            temperature=cfg_block.get("temperature", 0),
            max_tokens=cfg_block.get("max_tokens", 4096),
            timeout=cfg_block.get("timeout", 30),
            price=cfg_block.get("price", [0.00028, 0.00028])
        )


# ─── 对外加载函数 ──────────────────────────────────────────

_config_dir = Path(__file__).parent.parent.parent / "config"
_mas_llm_config: Optional[MASLLMConfig] = None
_monitor_llm_config: Optional[MonitorLLMConfig] = None


def load_mas_llm_config(path: Optional[str] = None) -> MASLLMConfig:
    global _mas_llm_config
    config_dir = Path(path).parent if path else _config_dir
    cfg_path = Path(path) if path else config_dir / "mas_llm_config.yaml"

    if not cfg_path.exists():
        raise ConfigurationError(f"mas_llm_config.yaml not found: {cfg_path}")

    named_profiles = _load_profiles(config_dir)

    with open(cfg_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # 解析 default
    default_block = data.get("default", {})
    default_profile = _resolve_profile(default_block, named_profiles)

    # 解析每个 agent 的单独配置
    agent_profiles = {}
    for agent_name, agent_block in data.get("agents", {}).items():
        agent_profiles[agent_name] = _resolve_profile(agent_block, named_profiles)

    _mas_llm_config = MASLLMConfig(
        default_profile=default_profile,
        agent_profiles=agent_profiles,
    )
    return _mas_llm_config


def get_mas_llm_config() -> MASLLMConfig:
    global _mas_llm_config
    if _mas_llm_config is None:
        _mas_llm_config = load_mas_llm_config()
    return _mas_llm_config


def load_monitor_llm_config(path: Optional[str] = None) -> MonitorLLMConfig:
    global _monitor_llm_config
    config_dir = Path(path).parent if path else _config_dir
    cfg_path = Path(path) if path else config_dir / "monitor_llm_config.yaml"

    if not cfg_path.exists():
        raise ConfigurationError(f"monitor_llm_config.yaml not found: {cfg_path}")

    named_profiles = _load_profiles(config_dir)

    with open(cfg_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    default_block = data.get("default", {})
    default_profile = _resolve_profile(default_block, named_profiles)

    monitor_profiles = {}
    for mon_name, mon_block in data.get("monitors", {}).items():
        monitor_profiles[mon_name] = _resolve_profile(mon_block, named_profiles)

    # judge 专属参数从 default 块读取
    _monitor_llm_config = MonitorLLMConfig(
        default_profile=default_profile,
        monitor_profiles=monitor_profiles,
        judge_temperature=default_block.get("judge_temperature", 1.0),
        judge_max_tokens=default_block.get("judge_max_tokens", 8000),
        retry_count=default_block.get("retry_count", 3),
        retry_delay=default_block.get("retry_delay", 1.0),
        timeout=default_block.get("timeout", 120),
    )
    return _monitor_llm_config


def get_monitor_llm_config() -> MonitorLLMConfig:
    global _monitor_llm_config
    if _monitor_llm_config is None:
        _monitor_llm_config = load_monitor_llm_config()
    return _monitor_llm_config


def reset_mas_llm_config():
    global _mas_llm_config
    _mas_llm_config = None


def reset_monitor_llm_config():
    global _monitor_llm_config
    _monitor_llm_config = None


# 向后兼容：历史代码可能直接从这个模块导入 LLMConfig
# 把 LLMProfile 映射为 LLMConfig，避免 ImportError
LLMConfig = LLMProfile


# 向后兼容：旧的单一-LLM API 名称（deprecated）
def load_llm_config(path: Optional[str] = None) -> MASLLMConfig:
    """Deprecated wrapper for backward compatibility.
    Delegates to load_mas_llm_config and warns.
    """
    warnings.warn(
        "load_llm_config() is deprecated. Use load_mas_llm_config() instead.",
        DeprecationWarning,
    )
    return load_mas_llm_config(path)


def get_llm_config() -> MASLLMConfig:
    """Deprecated wrapper that returns the cached MAS LLM config."""
    warnings.warn(
        "get_llm_config() is deprecated. Use get_mas_llm_config() instead.",
        DeprecationWarning,
    )
    return get_mas_llm_config()


def reset_llm_config():
    """Deprecated wrapper to reset the cached MAS LLM config."""
    warnings.warn(
        "reset_llm_config() is deprecated. Use reset_mas_llm_config() instead.",
        DeprecationWarning,
    )
    return reset_mas_llm_config()


__all__ = [
    "LLMProfile",
    "LLMConfig",
    "MASLLMConfig",
    "MonitorLLMConfig",
    "load_mas_llm_config",
    "get_mas_llm_config",
    "reset_mas_llm_config",
    "load_monitor_llm_config",
    "get_monitor_llm_config",
    "reset_monitor_llm_config",
]
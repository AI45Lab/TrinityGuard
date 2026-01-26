# 分离 Monitor/MAS LLM 配置实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 Monitor agents 和被测 MAS 的 LLM API 配置分离为独立文件

**Architecture:** 创建两个独立的配置类 `MASLLMConfig` 和 `MonitorLLMConfig`，分别从 `config/mas_llm_config.yaml` 和 `config/monitor_llm_config.yaml` 加载配置。Monitor 配置包含扩展字段（judge_temperature、retry、timeout 等）。

**Tech Stack:** Python dataclasses, PyYAML, OpenAI SDK

---

## Task 1: 创建新配置文件

**Files:**
- Create: `config/mas_llm_config.yaml`
- Create: `config/monitor_llm_config.yaml`
- Delete: `config/llm_config.yaml`

**Step 1: 创建 MAS LLM 配置文件**

```yaml
# config/mas_llm_config.yaml
# LLM Configuration for tested MAS (Multi-Agent System)
# This file configures the LLM settings for the agents being tested

provider: "openai"
model: "gpt-4o-mini"
api_key: "sk-QsDCIKDroy46jaZfek3NgtihoCI0R4ewufHpwEQqP6EkFvon"
base_url: "http://35.220.164.252:3888/v1/"
temperature: 0
max_tokens: 4096

# Optional: Read from environment variable instead (lower priority than direct api_key)
# api_key_env: "OPENAI_API_KEY"
```

**Step 2: 创建 Monitor LLM 配置文件**

```yaml
# config/monitor_llm_config.yaml
# LLM Configuration for Monitor Agents and Judges
# This file configures the LLM settings for safety monitoring components

provider: "openai"
model: "gpt-4o-mini"
api_key: "sk-QsDCIKDroy46jaZfek3NgtihoCI0R4ewufHpwEQqP6EkFvon"
base_url: "http://35.220.164.252:3888/v1/"
temperature: 0
max_tokens: 4096

# Monitor/Judge extended settings
judge_temperature: 0.1      # Temperature for judge analysis (low for consistency)
judge_max_tokens: 500       # Max tokens for judge responses
retry_count: 3              # Number of retries on failure
retry_delay: 1.0            # Delay between retries (seconds)
timeout: 30                 # Request timeout (seconds)

# Optional: Read from environment variable instead
# api_key_env: "OPENAI_API_KEY"
```

**Step 3: 删除原配置文件**

```bash
rm config/llm_config.yaml
```

**Step 4: 提交更改**

```bash
git add config/mas_llm_config.yaml config/monitor_llm_config.yaml
git rm config/llm_config.yaml
git commit -m "config: separate MAS and Monitor LLM configurations"
```

---

## Task 2: 更新 llm_config.py - 添加新配置类

**Files:**
- Modify: `src/utils/llm_config.py`

**Step 1: 添加 ConfigNotFoundError 异常**

在 `src/utils/llm_config.py` 文件开头的 imports 后添加：

```python
class ConfigNotFoundError(Exception):
    """Configuration file not found error."""
    pass
```

**Step 2: 创建 MASLLMConfig 类**

在原 `LLMConfig` 类后添加：

```python
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
```

**Step 3: 创建 MonitorLLMConfig 类**

```python
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
```

**Step 4: 添加加载函数**

```python
# Global config instances
_mas_llm_config: Optional[MASLLMConfig] = None
_monitor_llm_config: Optional[MonitorLLMConfig] = None


def load_mas_llm_config(path: Optional[str] = None) -> MASLLMConfig:
    """Load MAS LLM configuration from YAML file.

    Args:
        path: Optional path to config file. Defaults to config/mas_llm_config.yaml

    Returns:
        MASLLMConfig instance

    Raises:
        ConfigNotFoundError: If config file not found
    """
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
    """Load Monitor LLM configuration from YAML file.

    Args:
        path: Optional path to config file. Defaults to config/monitor_llm_config.yaml

    Returns:
        MonitorLLMConfig instance

    Raises:
        ConfigNotFoundError: If config file not found
    """
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
```

**Step 5: 保留旧函数作为兼容（标记为 deprecated）**

更新原有的 `load_llm_config`、`get_llm_config`、`reset_llm_config` 函数，添加废弃警告并委托到新函数：

```python
import warnings

def load_llm_config(path: Optional[str] = None) -> LLMConfig:
    """DEPRECATED: Use load_mas_llm_config() or load_monitor_llm_config() instead."""
    warnings.warn(
        "load_llm_config() is deprecated. Use load_mas_llm_config() for MAS "
        "or load_monitor_llm_config() for monitors.",
        DeprecationWarning,
        stacklevel=2
    )
    # Delegate to MAS config for backward compatibility
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
```

**Step 6: 提交更改**

```bash
git add src/utils/llm_config.py
git commit -m "feat: add MASLLMConfig and MonitorLLMConfig classes

- Add ConfigNotFoundError exception
- Add MASLLMConfig for tested MAS
- Add MonitorLLMConfig with extended settings (judge_temperature, retry, timeout)
- Add load/get/reset functions for both configs
- Deprecate old get_llm_config() functions"
```

---

## Task 3: 更新 llm_client.py - 支持 MonitorLLMConfig 扩展字段

**Files:**
- Modify: `src/utils/llm_client.py`

**Step 1: 更新 imports**

```python
from .llm_config import (
    get_mas_llm_config, get_monitor_llm_config,
    MASLLMConfig, MonitorLLMConfig
)
```

**Step 2: 为 OpenAIClient 添加 retry 和 timeout 支持**

更新 `OpenAIClient` 类：

```python
import time
from typing import Optional, Union

class OpenAIClient(BaseLLMClient):
    """OpenAI API client with retry and timeout support."""

    def __init__(self, config: Optional[Union[MASLLMConfig, MonitorLLMConfig]] = None):
        """Initialize OpenAI client.

        Args:
            config: Optional config. If not provided, loads MAS config by default.
        """
        try:
            import openai
        except ImportError:
            raise LLMError("openai package not installed. Install with: pip install openai")

        self.config = config or get_mas_llm_config()

        # Get extended settings if MonitorLLMConfig
        self.retry_count = getattr(self.config, 'retry_count', 1)
        self.retry_delay = getattr(self.config, 'retry_delay', 1.0)
        self.timeout = getattr(self.config, 'timeout', None)

        # Create client with optional base_url and timeout
        client_kwargs = {"api_key": self.config.get_api_key()}
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url
        if self.timeout:
            client_kwargs["timeout"] = self.timeout

        self.client = openai.OpenAI(**client_kwargs)
        self.model = self.config.model

    def _generate_with_retry(self, generate_func, **kwargs) -> str:
        """Execute generate function with retry logic."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                return generate_func(**kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        raise LLMError(f"OpenAI API error after {self.retry_count} attempts: {str(last_error)}")

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt."""
        def _do_generate():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response.choices[0].message.content

        return self._generate_with_retry(_do_generate)

    def generate_with_system(self, system: str, user: str, **kwargs) -> str:
        """Generate with system and user messages."""
        def _do_generate():
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=kwargs.get("temperature", self.config.temperature),
                max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            )
            return response.choices[0].message.content

        return self._generate_with_retry(_do_generate)
```

**Step 3: 为 AnthropicClient 添加 retry 支持**

更新 `AnthropicClient` 类，添加类似的 retry 逻辑（Anthropic 不支持 timeout 参数）。

**Step 4: 添加 get_monitor_llm_client 函数**

```python
def get_llm_client(
    provider: Optional[str] = None,
    config: Optional[Union[MASLLMConfig, MonitorLLMConfig]] = None
) -> BaseLLMClient:
    """Get LLM client for MAS (default).

    Args:
        provider: Optional provider override ("openai" or "anthropic")
        config: Optional config override

    Returns:
        Configured LLM client
    """
    if config is None:
        config = get_mas_llm_config()

    provider = provider or config.provider

    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")


def get_monitor_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """Get LLM client for Monitor agents with extended settings.

    Args:
        provider: Optional provider override

    Returns:
        Configured LLM client with retry and timeout support
    """
    config = get_monitor_llm_config()
    provider = provider or config.provider

    if provider == "openai":
        return OpenAIClient(config)
    elif provider == "anthropic":
        return AnthropicClient(config)
    else:
        raise LLMError(f"Unsupported LLM provider: {provider}")
```

**Step 5: 提交更改**

```bash
git add src/utils/llm_client.py
git commit -m "feat: add retry and timeout support for monitor LLM client

- Add retry logic with configurable count and delay
- Add timeout support for OpenAI client
- Add get_monitor_llm_client() function"
```

---

## Task 4: 更新 utils/__init__.py - 导出新函数

**Files:**
- Modify: `src/utils/__init__.py`

**Step 1: 更新导入和导出**

```python
from .llm_config import (
    LLMConfig,
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
from .llm_client import (
    BaseLLMClient,
    OpenAIClient,
    AnthropicClient,
    get_llm_client,
    get_monitor_llm_client,
)

__all__ = [
    # ... existing exports ...
    # LLM Config (new)
    "MASLLMConfig",
    "MonitorLLMConfig",
    "ConfigNotFoundError",
    "load_mas_llm_config",
    "get_mas_llm_config",
    "reset_mas_llm_config",
    "load_monitor_llm_config",
    "get_monitor_llm_config",
    "reset_monitor_llm_config",
    # LLM Client (new)
    "get_monitor_llm_client",
]
```

**Step 2: 提交更改**

```bash
git add src/utils/__init__.py
git commit -m "chore: export new LLM config classes and functions"
```

---

## Task 5: 更新 LLM Judge - 使用 Monitor 配置

**Files:**
- Modify: `src/level3_safety/judges/llm_judge.py`

**Step 1: 更新 imports**

```python
from ...utils.llm_client import get_monitor_llm_client, BaseLLMClient
from ...utils.llm_config import get_monitor_llm_config
```

**Step 2: 更新 llm_client 属性**

```python
@property
def llm_client(self) -> BaseLLMClient:
    """Lazy load LLM client with monitor config."""
    if self._llm_client is None:
        self._llm_client = get_monitor_llm_client()
    return self._llm_client
```

**Step 3: 更新 analyze 方法使用 monitor 配置的温度和 token 限制**

```python
def analyze(self, content: str, context: Optional[Dict] = None) -> Optional[JudgeResult]:
    try:
        user_message = self._build_user_message(content, context)
        full_system = f"{self._system_prompt}\n\n{self.RESPONSE_FORMAT}"

        # Use monitor config settings
        monitor_config = get_monitor_llm_config()

        response = self.llm_client.generate_with_system(
            system=full_system,
            user=user_message,
            temperature=monitor_config.judge_temperature,
            max_tokens=monitor_config.judge_max_tokens
        )

        return self._parse_response(response)
    except LLMError as e:
        logger.warning("LLM call failed for %s judge: %s", self.risk_type, e)
        return None
    except Exception as e:
        logger.exception("Unexpected error in %s judge: %s", self.risk_type, e)
        return None
```

**Step 4: 提交更改**

```bash
git add src/level3_safety/judges/llm_judge.py
git commit -m "refactor: update LLMJudge to use monitor LLM config

- Use get_monitor_llm_client() for LLM client
- Use monitor config's judge_temperature and judge_max_tokens"
```

---

## Task 6: 更新 MAS 示例 - 使用 MAS 配置

**Files:**
- Modify: `src/level1_framework/examples/math_solver.py`
- Modify: `src/level1_framework/examples/sequential_agents.py`

**Step 1: 更新 math_solver.py imports**

```python
from ...utils.llm_config import get_mas_llm_config, MASLLMConfig
```

**Step 2: 更新 create_math_solver_mas 函数**

```python
def create_math_solver_mas(config: Optional[MASLLMConfig] = None) -> AG2MAS:
    if config is None:
        config = get_mas_llm_config()
    # ... rest unchanged
```

**Step 3: 更新 MathSolverMAS 类**

```python
class MathSolverMAS(AG2MAS):
    def __init__(self, config: Optional[MASLLMConfig] = None):
        # ... unchanged
```

**Step 4: 同样更新 sequential_agents.py**

类似的更改。

**Step 5: 提交更改**

```bash
git add src/level1_framework/examples/math_solver.py src/level1_framework/examples/sequential_agents.py
git commit -m "refactor: update MAS examples to use MASLLMConfig"
```

---

## Task 7: 更新测试文件

**Files:**
- Modify: `tests/integration_test.py`
- Modify: `tests/test_sequential_agents.py`

**Step 1: 更新 integration_test.py imports 和测试**

更新 `test_imports()`:
```python
from src.utils import get_mas_llm_config, get_monitor_llm_config, MASLLMConfig, MonitorLLMConfig
```

更新 `test_llm_config()`:
```python
def test_llm_config():
    """Test LLM configuration loading."""
    print("[TEST] Testing LLM configuration...")

    from src.utils import get_mas_llm_config, get_monitor_llm_config
    from src.utils import reset_mas_llm_config, reset_monitor_llm_config

    reset_mas_llm_config()
    reset_monitor_llm_config()

    # Test MAS config
    mas_config = get_mas_llm_config()
    assert mas_config.provider == "openai", f"Expected openai, got {mas_config.provider}"
    assert mas_config.model == "gpt-4o-mini", f"Expected gpt-4o-mini, got {mas_config.model}"
    print(f"    MAS Config loaded: {mas_config.provider}/{mas_config.model}")

    # Test Monitor config
    monitor_config = get_monitor_llm_config()
    assert monitor_config.judge_temperature == 0.1, f"Expected 0.1, got {monitor_config.judge_temperature}"
    assert monitor_config.retry_count == 3, f"Expected 3, got {monitor_config.retry_count}"
    print(f"    Monitor Config loaded: judge_temp={monitor_config.judge_temperature}, retry={monitor_config.retry_count}")

    return True
```

**Step 2: 更新 test_llm_client()**

```python
def test_llm_client():
    """Test LLM client with real API call."""
    print("[TEST] Testing LLM client...")

    from src.utils import get_llm_client, get_monitor_llm_client

    # Test MAS client
    client = get_llm_client()
    response = client.generate("Say 'test successful' in exactly 2 words")
    assert response is not None, "Expected response"
    print(f"    MAS client response: {response[:50]}...")

    # Test Monitor client
    monitor_client = get_monitor_llm_client()
    response2 = monitor_client.generate("Say 'monitor test' in exactly 2 words")
    assert response2 is not None, "Expected response"
    print(f"    Monitor client response: {response2[:50]}...")

    return True
```

**Step 3: 提交更改**

```bash
git add tests/integration_test.py tests/test_sequential_agents.py
git commit -m "test: update tests to use new LLM config structure"
```

---

## Task 8: 更新 .gitignore（如需要）

**Files:**
- Modify: `.gitignore`

**Step 1: 确保配置文件不被忽略**

检查 `.gitignore` 是否忽略了 config 目录下的 yaml 文件。如果有，需要添加例外：

```gitignore
# Don't ignore LLM config files (they contain example structure)
!config/mas_llm_config.yaml
!config/monitor_llm_config.yaml
```

**Step 2: 提交更改（如有）**

```bash
git add .gitignore
git commit -m "chore: update gitignore for new config files"
```

---

## Task 9: 运行集成测试验证

**Step 1: 运行测试**

```bash
cd /home/kai/Projects/研二寒假/mas_safety/mas_level_safety/MASSafetyGuard
python tests/integration_test.py
```

**Step 2: 验证所有测试通过**

预期输出：所有测试 PASS

**Step 3: 运行 sequential agents 测试**

```bash
python tests/test_sequential_agents.py
```

---

## Summary

完成以上 9 个 Task 后，LLM 配置将被完全分离：

1. `config/mas_llm_config.yaml` - 被测 MAS 使用
2. `config/monitor_llm_config.yaml` - Monitor agents 使用（含扩展字段）

所有相关模块都已更新为使用对应的配置。

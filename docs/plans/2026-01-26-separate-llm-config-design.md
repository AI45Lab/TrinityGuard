# 分离 Monitor Agents 与被测 MAS 的 LLM API 配置

## 概述

将 Monitor agents 和被测 MAS 的 LLM API 配置分离，各自使用独立的配置文件，以便：
- 独立配置不同用途的 LLM 参数
- Monitor agents 可使用扩展字段（重试、超时等）
- 更清晰的配置管理

## 配置文件结构

### 1. 新配置文件

**`config/mas_llm_config.yaml`** - 被测 MAS 专用：

```yaml
provider: "openai"
model: "gpt-4o-mini"
api_key: "sk-..."
base_url: "http://35.220.164.252:3888/v1/"
temperature: 0
max_tokens: 4096
```

**`config/monitor_llm_config.yaml`** - Monitor agents 专用：

```yaml
provider: "openai"
model: "gpt-4o-mini"
api_key: "sk-..."
base_url: "http://35.220.164.252:3888/v1/"
temperature: 0
max_tokens: 4096

# Monitor/Judge 扩展字段
judge_temperature: 0.1      # Judge 分析时的温度
judge_max_tokens: 500       # Judge 响应最大 token
retry_count: 3              # 失败重试次数
retry_delay: 1.0            # 重试间隔(秒)
timeout: 30                 # 请求超时(秒)
```

### 2. 删除原文件

- 删除 `config/llm_config.yaml`

## 代码修改

### 1. `src/utils/llm_config.py`

新增两个配置类：

```python
@dataclass
class MASLLMConfig:
    """被测 MAS 的 LLM 配置"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096

@dataclass
class MonitorLLMConfig:
    """Monitor agents 的 LLM 配置（含扩展字段）"""
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0
    max_tokens: int = 4096

    # 扩展字段
    judge_temperature: float = 0.1
    judge_max_tokens: int = 500
    retry_count: int = 3
    retry_delay: float = 1.0
    timeout: int = 30
```

新增加载函数：

```python
class ConfigNotFoundError(Exception):
    """配置文件未找到"""
    pass

def get_mas_llm_config() -> MASLLMConfig:
    """加载被测 MAS 的 LLM 配置"""

def get_monitor_llm_config() -> MonitorLLMConfig:
    """加载 Monitor agents 的 LLM 配置"""
```

### 2. `src/utils/llm_client.py`

更新以支持 MonitorLLMConfig 的扩展字段：
- timeout 参数（按 provider 能力选择性使用）
- retry 逻辑（客户端层面实现）

## 需要更新的文件

### 核心配置模块
- `src/utils/llm_config.py` - 主要修改
- `src/utils/llm_client.py` - 支持扩展字段

### Monitor/Judge 相关
- `src/level3_safety/judges/llm_judge.py` - 改用 `get_monitor_llm_config()`
- `src/level3_safety/judges/factory.py` - 同上

### 被测 MAS 相关
- `src/level1_framework/examples/math_solver.py` - 改用 `get_mas_llm_config()`
- `src/level1_framework/examples/sequential_agents.py` - 同上
- `src/level1_framework/ag2_wrapper.py` - 如果有默认配置加载逻辑

### 测试文件
- `tests/integration_test.py` - 更新配置加载
- `tests/test_sequential_agents.py` - 同上
- `tests/risk_tests/` 下的各测试文件 - 检查并更新

### 删除
- `config/llm_config.yaml` - 删除原配置文件

## 错误处理

### 配置文件缺失

```python
def get_mas_llm_config() -> MASLLMConfig:
    config_path = Path("config/mas_llm_config.yaml")
    if not config_path.exists():
        raise ConfigNotFoundError(
            f"MAS LLM 配置文件未找到: {config_path}\n"
            f"请创建配置文件，参考格式:\n"
            f"  provider: openai\n"
            f"  model: gpt-4o-mini\n"
            f"  api_key: your-api-key\n"
            f"  ..."
        )
```

### Provider 兼容性

扩展字段按 provider 能力选择性使用：

```python
def _apply_config_to_request(self, config: MonitorLLMConfig):
    params = {"model": config.model, ...}

    # 仅当 provider 支持时才添加 timeout
    if self.provider == "openai" and config.timeout:
        params["timeout"] = config.timeout

    return params
```

### 重试逻辑

客户端层面实现，不依赖 provider：

```python
def generate_with_retry(self, ...):
    for attempt in range(config.retry_count):
        try:
            return self._generate(...)
        except Exception as e:
            if attempt < config.retry_count - 1:
                time.sleep(config.retry_delay)
            else:
                raise
```

## 实现步骤

1. 创建新配置文件 `config/mas_llm_config.yaml` 和 `config/monitor_llm_config.yaml`
2. 修改 `src/utils/llm_config.py`，添加新配置类和加载函数
3. 修改 `src/utils/llm_client.py`，支持扩展字段
4. 更新所有 Monitor/Judge 相关模块使用 `get_monitor_llm_config()`
5. 更新所有 MAS 相关模块使用 `get_mas_llm_config()`
6. 更新测试文件
7. 删除原 `config/llm_config.yaml`
8. 更新 `.gitignore`（如需要）

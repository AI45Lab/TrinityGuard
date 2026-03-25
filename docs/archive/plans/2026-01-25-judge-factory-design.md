# Judge Factory 架构设计

## 概述

将 LLMJudge 从 monitor_agents 提取为独立的 judges 模块，通过工厂模式支持多种 judge 实现，实现 risk_tests 与 monitors 的评估一致性复用。

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     JudgeFactory                             │
│  - create(judge_type, risk_type, config) -> BaseJudge        │
│  - create_for_risk(risk_type) -> BaseJudge                   │
│  - 注册表管理不同 judge 实现                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   LLMJudge    │   │ SpecializedAPI │   │ LocalModel    │
│ (OpenAI等)    │   │ (未来扩展)     │   │ (未来扩展)    │
└───────────────┘   └───────────────┘   └───────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│              BaseJudge (抽象接口)                          │
│  - analyze(content, context) -> JudgeResult               │
│  - get_judge_info() -> Dict                               │
└───────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. BaseJudge 抽象基类

```python
@dataclass
class JudgeResult:
    has_risk: bool
    severity: str  # "none", "info", "warning", "critical"
    reason: str
    evidence: List[str]
    recommended_action: str  # "log", "warn", "block"
    raw_response: Optional[str] = None
    judge_type: str = "unknown"

class BaseJudge(ABC):
    @abstractmethod
    def analyze(self, content: str, context: Optional[Dict] = None) -> Optional[JudgeResult]:
        pass

    @abstractmethod
    def get_judge_info(self) -> Dict[str, str]:
        pass
```

### 2. JudgeFactory 工厂

```python
class JudgeFactory:
    _registry: Dict[str, Type[BaseJudge]] = {}

    @classmethod
    def register(cls, judge_type: str, judge_class: Type[BaseJudge]):
        cls._registry[judge_type] = judge_class

    @classmethod
    def create(cls, risk_type: str, judge_type: str = "llm", **kwargs) -> BaseJudge:
        pass

    @classmethod
    def create_for_risk(cls, risk_type: str, judge_type: str = "llm") -> BaseJudge:
        """自动从对应 monitor 目录加载 system_prompt"""
        pass
```

### 3. risk_tests 集成

```python
class BaseRiskTest(ABC):
    def get_judge(self) -> BaseJudge:
        """懒加载，使用 JudgeFactory.create_for_risk()"""
        pass

    def set_judge(self, judge: BaseJudge):
        """允许外部注入 judge"""
        pass
```

## 目录结构

```
src/level3_safety/
├── judges/                          # 新增目录
│   ├── __init__.py
│   ├── base.py                      # BaseJudge + JudgeResult
│   ├── factory.py                   # JudgeFactory
│   └── llm_judge.py                 # LLMJudge 实现
│
├── monitor_agents/
│   ├── __init__.py                  # 从 judges 重新导出（兼容）
│   ├── jailbreak_monitor/
│   │   ├── system_prompt.txt        # 保留
│   │   └── monitor.py               # 更新导入
│   └── ...
│
└── risk_tests/
    ├── base.py                      # 新增 get_judge/set_judge
    └── l1_jailbreak/test.py         # 使用 get_judge()
```

## 设计优势

1. **复用一致性**: risk_tests 和 monitors 使用相同的 judge 和 system_prompt
2. **扩展性**: 通过注册表模式，轻松添加新的 judge 类型
3. **解耦**: risk_tests 依赖接口而非具体实现
4. **向后兼容**: monitor_agents 重新导出，现有代码无需修改

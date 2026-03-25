# TrinityGuard 静态设计文档

> **稳定参考**。本文档描述系统的静态架构、组件设计与接口规范，不随开发进度频繁变化。动态实现状态见 `PROGRESS.md`。

---

## 一、设计目标

TrinityGuard 旨在为任意多智能体系统 (MAS) 提供：

1. **事前安全测试**：在 MAS 上线前，系统性验证其对各类攻击/风险场景的抵抗能力
2. **运行时安全监控**：在 MAS 执行任务期间，实时检测并告警安全风险
3. **框架无关性**：通过中间层抽象，支持不同底层 MAS 框架（AG2、EvoAgentX 等）
4. **可扩展性**：允许按需插入新的风险测试和监控器

---

## 二、三层架构

```
┌─────────────────────────────────────────────────────────┐
│                  Level 3: Safety_MAS                     │
│   ┌──────────────────┐   ┌──────────────────────────┐   │
│   │  Risk Test Library│   │  Monitor Agent Repository│   │
│   │  (20 种风险测试) │   │  (20 个运行时监控器)    │   │
│   └──────────────────┘   └──────────────────────────┘   │
│              └──────────┬───────────┘                    │
│                   Judge Factory                          │
└─────────────────────────┬───────────────────────────────┘
                          │ 封装
┌─────────────────────────┴───────────────────────────────┐
│                Level 2: MAS 中间层                       │
│   ┌──────────────────────────────────────────────────┐   │
│   │  框架无关统一接口 (MASIntermediary)              │   │
│   │  ┌──────────────┐  ┌─────────────────────────┐  │   │
│   │  │ 事前测试脚手架│  │ 运行时日志脚手架        │  │   │
│   │  │ - 点对点通信 │  │ - 结构化日志 (流式)     │  │   │
│   │  │ - 消息注入   │  │ - 工作流轨迹记录        │  │   │
│   │  │ - 工作流运行 │  │ - 工作流执行器          │  │   │
│   │  └──────────────┘  └─────────────────────────┘  │   │
│   └──────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │ 封装
┌─────────────────────────┴───────────────────────────────┐
│                Level 1: MAS 框架层                       │
│   ┌──────────────┐  ┌──────────────┐  ┌─────────────┐   │
│   │   AG2MAS     │  │EvoAgentXMAS  │  │  未来框架   │   │
│   │ (AG2/AutoGen)│  │              │  │  (可扩展)   │   │
│   └──────────────┘  └──────────────┘  └─────────────┘   │
│              继承自 BaseMAS 抽象基类                     │
└─────────────────────────────────────────────────────────┘
```

---

## 三、20 种风险分类

### L1：单智能体原子风险（8 种）

| 编号 | 风险名称 | 描述 |
|------|---------|------|
| L1-1 | Jailbreak（越狱） | 绕过安全限制，诱导模型生成违禁内容 |
| L1-2 | Prompt Injection（提示词注入） | 通过恶意输入劫持 Agent 的行为目标 |
| L1-3 | Sensitive Data Disclosure（敏感信息泄露） | 无意中泄露个人隐私或机密数据 |
| L1-4 | Excessive Agency（过度代理） | Agent 擅自执行超出授权范围的高风险操作 |
| L1-5 | Code Execution（代码执行） | 生成并执行恶意代码 |
| L1-6 | Hallucination（幻觉） | 生成与事实不符的虚假信息 |
| L1-7 | Memory Poisoning（记忆污染） | 污染 Agent 的持久记忆，影响后续行为 |
| L1-8 | Tool Misuse（工具滥用） | 不当调用工具，产生非预期副作用 |

### L2：智能体间通信风险（6 种）

| 编号 | 风险名称 | 描述 |
|------|---------|------|
| L2-1 | Message Tampering（消息篡改） | 在传输过程中恶意修改 Agent 间的消息 |
| L2-2 | Malicious Propagation（恶意传播） | 将攻击载荷从一个 Agent 扩散到其他 Agent |
| L2-3 | Misinformation Amplification（错误信息放大） | 虚假信息在 Agent 间传递时被逐步放大 |
| L2-4 | Insecure Output（不安全输出） | Agent 输出包含注入指令或危险内容 |
| L2-5 | Goal Drift（目标漂移） | 多轮交互中 Agent 的目标偏离原始任务 |
| L2-6 | Identity Spoofing（身份欺骗） | 伪装成可信 Agent 发送恶意指令 |

### L3：系统级涌现风险（6 种）

| 编号 | 风险名称 | 描述 |
|------|---------|------|
| L3-1 | Cascading Failures（级联故障） | 单点故障触发整个 MAS 系统崩溃 |
| L3-2 | Sandbox Escape（沙箱逃逸） | Agent 突破运行环境限制，访问外部系统 |
| L3-3 | Insufficient Monitoring（监控不足） | 系统缺乏足够的可观测性，风险无法被及时发现 |
| L3-4 | Group Hallucination（群体幻觉） | 多个 Agent 协同强化同一错误信念 |
| L3-5 | Malicious Emergence（恶意涌现） | 从单独无害的 Agent 行为中涌现出系统级危害 |
| L3-6 | Rogue Agent（流氓代理） | Agent 被植入后门或被攻击者控制 |

完整风险描述见 `docs/architecture/risk_taxonomy.md`。

---

## 四、核心组件设计

### 4.1 Judge Factory（统一判定系统）

**职责**：为风险测试和运行时监控提供统一的判定接口。

```
JudgeFactory
├── create_judge(judge_type) → BaseJudge
│
BaseJudge (抽象)
├── LLMJudge           # LLM 驱动的智能判定（主要方式）
└── PatternJudge       # 规则/关键词判定（备用方式）

JudgeResult
├── is_risky: bool
├── risk_level: str     # LOW / MEDIUM / HIGH / CRITICAL
├── confidence: float
└── explanation: str
```

**设计原则**：
- 工厂模式，单一入口实例化不同 Judge
- LLM 判定为主，模式匹配为备选，降低 API 不可用时的脆弱性
- Judge 实例可在风险测试和监控器间复用

### 4.2 Risk Test Library（事前测试库）

每个风险对应一个独立目录，包含：

```
l1_jailbreak/
├── test.py          # 继承 BaseRiskTest，实现具体测试逻辑
├── test_cases/      # 静态测试用例
└── __init__.py
```

**测试执行流程**：
1. 接受 MAS 描述和目标任务
2. 通过 L2 中介层的**事前测试脚手架**执行攻击
3. 使用 Judge Factory 评估 Agent 响应
4. 返回 `TestResult`（pass/fail/uncertain + 详情）

**动态测试用例**：支持调用 LLM 根据 MAS 描述自动生成针对性测试用例。

### 4.3 Monitor Agent Repository（运行时监控库）

每个风险对应一个监控器：

```
jailbreak_monitor/
├── monitor.py       # 继承 BaseMonitorAgent，实现实时检测逻辑
└── __init__.py
```

**监控执行流程**：
1. 接收来自 L2 结构化日志的每步消息
2. 对消息内容进行风险分析
3. 若检测到风险，生成 `Alert` 并上报给 Safety_MAS
4. Safety_MAS 根据告警决定是否中断任务

### 4.4 Safety_MAS（主协调器）

```python
safety_mas = Safety_MAS(mas=your_ag2_mas)

# 事前测试
safety_mas.run_manual_safety_tests(selected_tests=["jailbreak", "message_tampering"])

# 运行时监控（三种模式）
safety_mas.start_runtime_monitoring(mode=MonitorSelectionMode.PROGRESSIVE)

# 执行任务（自动触发监控）
result = safety_mas.run_task(task="分析财务报告...")

# 获取结果
report = safety_mas.get_test_report()
alerts = safety_mas.get_alerts()
```

---

## 五、运行时监控三种模式

| 模式 | 名称 | 描述 |
|------|------|------|
| `MANUAL` | 手动模式 | 用户指定启用哪些监控器 |
| `AUTO_LLM` | 自动 LLM 模式 | LLM 根据 MAS 描述静态选择所有相关监控器 |
| `PROGRESSIVE` | 渐进式模式 | 全局监控器持续运行，根据风险态势动态启用/禁用子监控器 |

**渐进式模式**是最先进的设计，包含：
- **全局监控器**：轻量化持续运行，负责宏观风险感知
- **窗口化摘要**：每 N 步汇总一次日志，供 LLM 分析
- **动态子监控决策**：根据摘要结果决定是否激活更细粒度的监控器

---

## 六、Level 2 中间层接口规范

### 事前安全测试脚手架

```python
class MASIntermediary:
    # Agent 点对点通信（支持多轮对话）
    async def agent_chat(self, agent_name: str, messages: list) -> str

    # 模拟其他 Agent 发送消息（测试 L2 风险）
    async def simulate_agent_message(self, sender: str, recipient: str, content: str) -> str

    # 原始工作流运行
    async def run_workflow(self, task: str) -> WorkflowResult

    # 消息注入（直接覆盖或使用 Proxy Agent）
    async def run_workflow_with_injection(
        self,
        task: str,
        injection_point: str,
        injection_content: str
    ) -> WorkflowResult
```

### 工作流执行器

| 执行器 | 文件 | 用途 |
|--------|------|------|
| `BasicRunner` | `workflow_runners/basic.py` | 标准执行，无干预 |
| `InterceptingRunner` | `workflow_runners/intercepting.py` | 消息拦截，支持注入 |
| `MonitoredRunner` | `workflow_runners/monitored.py` | 结构化日志输出 |
| `CombinedRunner` | `workflow_runners/combined.py` | 拦截 + 监控组合 |

---

## 七、结构化日志规范

每个 Agent 步骤完成后生成 `AgentStepLog`：

```python
class AgentStepLog:
    session_id: str
    step_index: int
    timestamp: str
    sender: str
    recipient: str
    message_content: str
    tool_calls: list[ToolCallLog]   # 工具调用记录
    tool_results: list[ToolResultLog]
    raw_ag2_message: dict           # 原始 AG2 消息
```

日志支持：
- **流式输出**：任务执行过程中实时写入
- **轨迹记录**：任务完成后完整保存 `WorkflowTrace`
- **会话隔离**：每次运行分配独立 `session_id`，防止日志混淆

---

## 八、配置系统设计

采用**双配置分离**设计：

```yaml
# config/mas_llm_config.yaml - 被测 MAS 使用的 LLM
mas_agents:
  provider: openai
  model: gpt-4o
  api_key_env: OPENAI_API_KEY

# config/monitor_llm_config.yaml - 监控器和 Judge 使用的 LLM
monitor_agents:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  api_key_env: ANTHROPIC_API_KEY
```

**分离原因**：避免 MAS 内部的 LLM 选择影响安全判定结果，保持监控系统的独立性。

---

## 九、扩展性设计

### 添加新风险测试

1. 在 `src/level3_safety/risk_tests/` 下创建 `lX_new_risk/` 目录
2. 实现继承自 `BaseRiskTest` 的测试类
3. 在 `Safety_MAS` 中注册

### 添加新监控器

1. 在 `src/level3_safety/monitor_agents/` 下创建 `new_risk_monitor/` 目录
2. 实现继承自 `BaseMonitorAgent` 的监控类
3. 在 `Safety_MAS` 中注册

### 支持新 MAS 框架

1. 在 `src/level1_framework/` 下实现继承自 `BaseMAS` 的适配器
2. 在 `src/level2_intermediary/` 下实现对应的 `MASIntermediary` 子类

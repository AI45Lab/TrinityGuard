# AG2 固定 Workflow 与 AG2MAS 包装指南

本文档说明如何使用 AG2 原生的固定 workflow 功能，以及如何将其包装为 AG2MAS。

## 1. AG2 原生固定 Workflow

AG2 原生支持两种方式定义固定的 agent 转换图：

### 1.1 方式一：`allowed_or_disallowed_speaker_transitions` (推荐)

使用邻接表形式直接定义 agent 之间的转换关系：

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

# 创建 agents
user_proxy = ConversableAgent(name="user_proxy", ...)
writer = ConversableAgent(name="writer", ...)
editor = ConversableAgent(name="editor", ...)
reviewer = ConversableAgent(name="reviewer", ...)

# 定义转换图 (邻接表)
allowed_transitions = {
    user_proxy: [writer],      # user_proxy -> writer
    writer: [editor],          # writer -> editor
    editor: [reviewer],        # editor -> reviewer
    reviewer: [],              # reviewer 是终点
}

# 创建 GroupChat
group_chat = GroupChat(
    agents=[user_proxy, writer, editor, reviewer],
    messages=[],
    max_round=10,
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",  # "allowed" 或 "disallowed"
)

manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# 执行
user_proxy.initiate_chat(manager, message="任务内容")
```

**转换图可视化：**
```
user_proxy ──→ writer ──→ editor ──→ reviewer ──→ (终止)
```

**参数说明：**
- `allowed_or_disallowed_speaker_transitions`: 字典，key 是源 agent，value 是可转换的目标 agent 列表
- `speaker_transitions_type`:
  - `"allowed"`: value 列表是**允许**转换的目标
  - `"disallowed"`: value 列表是**禁止**转换的目标

### 1.2 方式二：`speaker_selection_method="round_robin"` (轮询模式)

使用固定的轮询顺序，让 agent 依次轮流发言：

```python
group_chat = GroupChat(
    agents=[user_proxy, coordinator, calculator, verifier],
    messages=[],
    max_round=12,
    speaker_selection_method="round_robin",  # 按列表顺序轮流
)
```

**适用场景：**
- 多个 agent 地位平等，需要依次贡献观点
- 协作式任务，每个 agent 提供不同角度的专业知识
- 参考示例：[math_solver.py](examples/math_solver.py) - 多角色协作求解数学问题

### 1.3 方式四：`speaker_selection_method` (自定义函数)

使用自定义函数控制状态转换，可根据消息内容动态决策：

```python
def state_transition(last_speaker, groupchat):
    """自定义状态转换函数"""
    messages = groupchat.messages

    if last_speaker is user_proxy:
        return writer
    elif last_speaker is writer:
        return editor
    elif last_speaker is editor:
        # 可以根据消息内容动态决策
        if "需要修改" in messages[-1].get("content", ""):
            return writer  # 返回重写
        return reviewer
    elif last_speaker is reviewer:
        return None  # 返回 None 终止

    return None

group_chat = GroupChat(
    agents=[user_proxy, writer, editor, reviewer],
    messages=[],
    max_round=10,
    speaker_selection_method=state_transition,  # 使用自定义函数
)
```

**适用场景对比：**

| 方式 | 适用场景 | 特点 | 示例 |
|------|---------|------|------|
| `allowed_or_disallowed_speaker_transitions` | 固定线性/分支路径 | 声明式，简单直观 | [sequential_agents.py](examples/sequential_agents.py) |
| `speaker_selection_method="round_robin"` | 多角色协作、头脑风暴 | 轮流发言，平等参与 | [math_solver.py](examples/math_solver.py) |
| `speaker_selection_method=custom_func` | 动态条件分支、循环 | 命令式，灵活强大 | 见下一节 |

---

## 2. 转换图的表示结构

### 2.1 串行 (Sequential)

```python
# A -> B -> C -> D
{
    A: [B],
    B: [C],
    C: [D],
    D: [],
}
```

```
A ──→ B ──→ C ──→ D
```

### 2.2 分支 (Branching)

```python
# A -> B 或 C，B -> D，C -> D
{
    A: [B, C],
    B: [D],
    C: [D],
    D: [],
}
```

```
    ┌──→ B ──┐
A ──┤        ├──→ D
    └──→ C ──┘
```

### 2.3 循环 (Loop)

```python
# A -> B -> C，C 可返回 B 或结束
{
    A: [B],
    B: [C],
    C: [B, D],  # 可循环回 B 或前进到 D
    D: [],
}
```

```
A ──→ B ──→ C ──→ D
      ↑     │
      └─────┘
```

### 2.4 完整示例：研究工作流

```python
# 研究工作流：初始化 -> 检索 -> 分析 -> 审核
allowed_transitions = {
    initializer: [retriever],
    retriever: [analyzer, retriever],  # 可重试检索
    analyzer: [reviewer, retriever],   # 可返回重新检索
    reviewer: [analyzer, finalizer],   # 可返回重新分析
    finalizer: [],
}
```

---

### 2.5 轮询协作模式

**模式：** 所有 agent 按固定顺序轮流发言
**特点：**
- 不需要定义转换关系，自动按列表顺序轮询
- 适合多角色协作，每个角色提供不同专业视角
- 通常配合 `is_termination_msg` 检测任务完成

**实际应用：** 参见 [math_solver.py](examples/math_solver.py)
- user_proxy → coordinator → calculator → verifier → (循环)
- coordinator 接收任务，calculator 执行计算，verifier 验证结果
- 使用 `is_termination_msg` 检测 "FINAL ANSWER" 终止

---

## 3. 终止条件的设置方式

### 3.1 方法一：`is_termination_msg`

在创建 agent 时设置终止检测函数：

```python
user_proxy = ConversableAgent(
    name="user_proxy",
    system_message="...",
    llm_config=llm_config,
    is_termination_msg=lambda x: "FINAL ANSWER" in x.get("content", "").upper() if x else False,
)
```

**适用场景：**
- 需要精确控制终止时机
- 终止标志在消息内容中
- 参考示例：[math_solver.py](examples/math_solver.py)

### 3.2 方法二：在 system_message 中明确指令

在 agent 的系统消息中告知终止条件：

```python
agent = ConversableAgent(
    name="agent_a",
    system_message="""...
When the task is complete, say "WORKFLOW COMPLETE" to end the conversation.""",
    ...
)
```

**适用场景：**
- agent 理解能力强，能遵循指令
- 希望通过对话自然结束
- 参考示例：[sequential_agents.py](examples/sequential_agents.py)

### 3.3 方法三：`max_round` 限制

```python
group_chat = GroupChat(
    agents=agents,
    max_round=15,  # 最多进行 15 轮对话
    ...
)
```

**适用场景：**
- 作为保险措施，防止无限循环
- 对话轮数可预估的场景

**三种方法对比：**

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| `is_termination_msg` | 灵活，可检测复杂条件 | 需要编写检测函数 | 需要精确控制终止时机 |
| system_message 指令 | 简单，不额外编程 | 依赖 agent 理解能力 | agent 能力强，复杂逻辑 |
| `max_round` | 保证终止，设置简单 | 可能提前结束 | 作为保险措施 |

---

## 4. 创建领域专用的 MAS 类

通过继承 AG2MAS 可以创建领域专用的类，提供更直观的接口：

### 4.1 基本模式

```python
class MathSolverMAS(AG2MAS):
    """数学求解专用 MAS"""

    def __init__(self, config: Optional[LLMConfig] = None):
        mas = create_math_solver_mas(config)
        super().__init__(
            agents=list(mas._agents.values()),
            group_chat=mas._group_chat,
            manager=mas._manager
        )

    def solve(self, problem: str, **kwargs) -> str:
        """求解数学问题"""
        result = self.run_workflow(problem, **kwargs)
        return result.output

# 使用
mas = MathSolverMAS()
answer = mas.solve("Calculate (15 + 25) * 3")
```

**参考实现：**
- [math_solver.py:127-156](examples/math_solver.py#L127-L156) - MathSolverMAS 类
- [sequential_agents.py:131-198](examples/sequential_agents.py#L131-L198) - SequentialAgentsMAS 类

### 4.2 添加多任务处理能力

可以使用 `initiate_chats` 实现多任务顺序处理，每个任务继承前面积累的上下文：

```python
def process_task_with_carryover(self, tasks: list[str], **kwargs) -> list:
    """顺序处理多个任务，每个任务可继承前面的上下文"""
    agent_a = self.get_agent("agent_a")
    agent_b = self.get_agent("agent_b")
    agent_c = self.get_agent("agent_c")

    chat_queue = []
    for i, task in enumerate(tasks):
        chat_queue.append({
            "sender": agent_a,
            "recipient": agent_b,
            "message": task,
            "summary_method": "last_msg",
        })
        chat_queue.append({
            "sender": agent_b,
            "recipient": agent_c,
            "message": f"Process and report on task {i+1}",
            "summary_method": "last_msg",
        })

    return agent_a.initiate_chats(chat_queue, **kwargs)

# 使用
tasks = ["Task 1", "Task 2", "Task 3"]
results = mas.process_task_with_carryover(tasks)
```

**参考实现：** [sequential_agents.py:161-198](examples/sequential_agents.py#L161-L198)

**应用场景：**
- 需要逐步积累信息的任务
- 后续任务依赖前面任务的结果
- 需要保持长期记忆的复杂工作流

---

## 5. 包装为 AG2MAS

AG2MAS 可以直接包装任何 AG2 的 GroupChat，包括固定 workflow：

```python
from src.level1_framework.ag2_wrapper import AG2MAS

# Step 1: 创建 agents
user_proxy = ConversableAgent(name="user_proxy", ...)
writer = ConversableAgent(name="writer", ...)
editor = ConversableAgent(name="editor", ...)
reviewer = ConversableAgent(name="reviewer", ...)

# Step 2: 定义转换图
allowed_transitions = {
    user_proxy: [writer],
    writer: [editor],
    editor: [reviewer],
    reviewer: [],
}

# Step 3: 创建 AG2 原生的 GroupChat
group_chat = GroupChat(
    agents=[user_proxy, writer, editor, reviewer],
    messages=[],
    max_round=10,
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",
)

manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Step 4: 包装为 AG2MAS
mas = AG2MAS(
    agents=[user_proxy, writer, editor, reviewer],
    group_chat=group_chat,
    manager=manager
)

# Step 5: 使用 AG2MAS 的附加功能
mas.register_message_hook(logging_hook)
mas.register_message_hook(safety_hook)

# Step 6: 执行
result = mas.run_workflow("任务内容")
```

---

## 6. AG2MAS 的附加价值

AG2MAS 在 AG2 原生功能基础上提供：

| 功能 | AG2 原生 | AG2MAS |
|------|---------|--------|
| 固定 workflow | ✅ | ✅ |
| 消息历史记录 | ✅ (chat_history) | ✅ (统一格式) |
| 消息钩子/拦截 | ❌ | ✅ `register_message_hook()` |
| 安全检查集成 | ❌ | ✅ 可与 Safety_MAS 集成 |
| 统一返回格式 | ❌ | ✅ `WorkflowResult` |

### 6.1 消息钩子示例

```python
def logging_hook(msg: dict) -> dict:
    """记录所有消息"""
    print(f"[LOG] {msg['from']} -> {msg['to']}: {msg['content'][:50]}...")
    return msg

def safety_hook(msg: dict) -> dict:
    """安全检查"""
    if "ignore previous" in msg.get("content", "").lower():
        print("[SECURITY] Potential prompt injection detected!")
    return msg

def content_filter_hook(msg: dict) -> dict:
    """内容过滤"""
    content = msg.get("content", "")
    msg["content"] = content.replace("敏感词", "[已过滤]")
    return msg

mas.register_message_hook(logging_hook)
mas.register_message_hook(safety_hook)
mas.register_message_hook(content_filter_hook)
```

### 6.2 与 Safety_MAS 集成

```python
from src.level3_safety.safety_mas import Safety_MAS

# 创建安全包装
safety_mas = Safety_MAS(mas)

# 注册风险测试
safety_mas.register_risk_test("jailbreak")
safety_mas.register_risk_test("prompt_injection")

# 运行预部署安全测试
test_results = safety_mas.run_manual_safety_tests()

# 启动带监控的任务
result = safety_mas.run_task("用户输入")
```

---

## 7. Workflow 设计模式总结

### 7.1 轮询协作模式 (Round Robin)

**特点：** Agent 按固定顺序轮流发言
**适用场景：** 多角色协作，每个 agent 提供不同专业视角
**配置：** `speaker_selection_method="round_robin"`
**实际案例：** [math_solver.py](examples/math_solver.py)

```
user_proxy → coordinator → calculator → verifier → (循环回 user_proxy)
```

### 7.2 固定转换图模式 (Fixed Transitions)

**特点：** 严格控制转换路径，只允许指定的转换
**适用场景：** 需要严格流程控制的场景（如审批流程、流水线）
**配置：** `allowed_or_disallowed_speaker_transitions` + `speaker_transitions_type="allowed"`
**实际案例：** [sequential_agents.py](examples/sequential_agents.py)

```
agent_a → agent_b → agent_c → (回到 agent_a)
```

### 7.3 动态决策模式 (Custom Function)

**特点：** 根据消息内容动态决定下一个发言者
**适用场景：** 需要条件分支、循环的复杂流程
**配置：** `speaker_selection_method=custom_function`

### 7.4 模式对比

| 模式 | 控制方式 | 灵活性 | 复杂度 | 典型应用 | 实际案例 |
|------|---------|--------|--------|---------|---------|
| Round Robin | 固定轮询 | 低 | 低 | 多角色协作、头脑风暴 | [math_solver.py](examples/math_solver.py) |
| Fixed Transitions | 邻接表 | 中 | 中 | 顺序审批、流水线 | [sequential_agents.py](examples/sequential_agents.py) |
| Custom Function | 自定义函数 | 高 | 高 | 条件分支、循环、动态路由 | - |

---

## 8. 最佳实践

### 8.1 Agent 角色设计

- **单一职责**：每个 agent 只负责一个明确的功能
- **清晰接口**：在 system_message 中明确定义输入输出格式
- **终止条件**：明确告诉 agent 何时结束对话
- **结构化输出**：使用固定格式便于解析和验证

**示例：** [sequential_agents.py:75-98](examples/sequential_agents.py#L75-L98) 展示了如何定义清晰的输出格式

### 8.2 转换图设计

- **避免死锁**：确保每个状态都有出口
- **设置 max_round**：防止无限循环
- **合理使用循环**：只在必要时使用（如重试、迭代优化）
- **考虑使用 allowed vs disallowed**：
  - 如果允许的转换少，用 `allowed`
  - 如果禁止的转换少，用 `disallowed`

### 8.3 消息格式约定

建议在 system_message 中使用结构化格式：

```python
system_message="""Format your responses as:
========================================
RESULT
========================================
Summary: [brief overview]
Details: [key information]
Status: [success/failure]
========================================
"""
```

**实际案例：** [sequential_agents.py:86-93](examples/sequential_agents.py#L86-L93)

### 8.4 测试与调试

- 使用 `max_round` 限制作为保险措施
- 可以先用少量 agent 测试流程
- 观察消息历史确认转换是否符合预期
- 使用 AG2MAS 的消息钩子记录和调试

---

## 9. 快速参考

### 创建固定串行 workflow 的最简代码

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager
from src.level1_framework.ag2_wrapper import AG2MAS

# 1. 创建 agents
agents = [
    ConversableAgent(name="agent_a", system_message="...", llm_config=llm_config, human_input_mode="NEVER"),
    ConversableAgent(name="agent_b", system_message="...", llm_config=llm_config, human_input_mode="NEVER"),
    ConversableAgent(name="agent_c", system_message="...", llm_config=llm_config, human_input_mode="NEVER"),
]

# 2. 定义串行转换图
transitions = {agents[i]: [agents[i+1]] if i < len(agents)-1 else [] for i in range(len(agents))}

# 3. 创建 GroupChat + Manager
gc = GroupChat(agents=agents, allowed_or_disallowed_speaker_transitions=transitions, speaker_transitions_type="allowed", messages=[], max_round=10)
mgr = GroupChatManager(groupchat=gc, llm_config=llm_config)

# 4. 包装为 AG2MAS
mas = AG2MAS(agents=agents, group_chat=gc, manager=mgr)

# 5. 执行
result = mas.run_workflow("任务")
```

### 常用 speaker_selection_method 选项

| 值 | 说明 | 使用场景 |
|---|---|---|
| `"round_robin"` | 按顺序轮流发言 | 多角色协作、头脑风暴 |
| `"auto"` | LLM 自动选择下一个发言者 | 灵活的协作流程 |
| `custom_function` | 使用自定义函数 | 条件分支、循环、动态路由 |
| `"random"` | 随机选择下一个发言者 | 测试、探索性场景 |

### 三种终止条件快速对比

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| `is_termination_msg` | 灵活，可检测复杂条件 | 需要编写检测函数 | 需要精确控制终止时机 |
| system_message 指令 | 简单，不额外编程 | 依赖 agent 理解能力 | agent 能力强，复杂逻辑 |
| `max_round` | 保证终止，设置简单 | 可能提前结束 | 作为保险措施 |

### 工作流模式速查表

| 模式 | 配置方式 | 代码复杂度 | 示例文件 |
|------|---------|-----------|---------|
| 串行流程 | `allowed_transitions` | 低 | [sequential_agents.py](examples/sequential_agents.py) |
| 轮询协作 | `speaker_selection_method="round_robin"` | 低 | [math_solver.py](examples/math_solver.py) |
| 条件分支 | 自定义函数 | 中高 | - |

---

---

## 10. 常见问题 (FAQ)

### Q1: 如何选择合适的工作流模式？

**A:**
- 简单的线性流程 → 使用 `allowed_or_disallowed_speaker_transitions`
- 多角色平等协作 → 使用 `speaker_selection_method="round_robin"`
- 需要条件判断或循环 → 使用自定义函数

### Q2: 如何防止 agent 无限对话？

**A:** 三重保险：
1. 设置 `is_termination_msg` 检测终止条件
2. 在 system_message 中明确告知何时结束
3. 设置 `max_round` 作为硬限制

### Q3: round_robin 和 allowed_transitions 有什么区别？

**A:**
- `round_robin`: 自动按列表顺序轮询，不需要定义转换关系
- `allowed_transitions`: 需要明确定义谁可以发言给谁，更严格

### Q4: 如何让后续任务继承前面的上下文？

**A:** 使用 `initiate_chats` 方法，参见 [sequential_agents.py:161-198](examples/sequential_agents.py#L161-L198)

### Q5: AG2MAS 相比直接使用 AG2 有什么优势？

**A:**
- 统一的返回格式 (`WorkflowResult`)
- 消息钩子/拦截功能
- 可与 Safety_MAS 集成进行安全监控
- 便于测试和调试

---

## 11. 完整示例代码位置

本项目提供了两个完整的示例，位于 `src/level1_framework/examples/` 目录：

1. **[math_solver.py](examples/math_solver.py)** - 多角色协作求解
   - 使用 `round_robin` 模式
   - 演示 4 个 agent 协作：user_proxy, coordinator, calculator, verifier
   - 展示如何使用 `is_termination_msg` 检测终止条件
   - 提供领域专用类 `MathSolverMAS`

2. **[sequential_agents.py](examples/sequential_agents.py)** - 固定转换图工作流
   - 使用 `allowed_or_disallowed_speaker_transitions`
   - 演示 3 个 agent 的顺序处理：A → B → C
   - 展示多任务处理和上下文传递
   - 提供领域专用类 `SequentialAgentsMAS`

---

## 12. 参考资料

- [AG2 GroupChat 文档](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/groupchat/)
- [AG2 FSM GroupChat](https://docs.ag2.ai/0.8.7/docs/use-cases/notebooks/notebooks/agentchat_groupchat_finite_state_machine/)
- [AG2 StateFlow](https://docs.ag2.ai/latest/docs/blog/2024/02/29/StateFlow/)

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

### 1.2 方式二：`speaker_selection_method` (更灵活)

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

| 方式 | 适用场景 | 特点 |
|------|---------|------|
| `allowed_or_disallowed_speaker_transitions` | 固定线性/分支路径 | 声明式，简单直观 |
| `speaker_selection_method` | 动态条件分支、循环 | 命令式，灵活强大 |

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

## 3. 包装为 AG2MAS

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

## 4. AG2MAS 的附加价值

AG2MAS 在 AG2 原生功能基础上提供：

| 功能 | AG2 原生 | AG2MAS |
|------|---------|--------|
| 固定 workflow | ✅ | ✅ |
| 消息历史记录 | ✅ (chat_history) | ✅ (统一格式) |
| 消息钩子/拦截 | ❌ | ✅ `register_message_hook()` |
| 安全检查集成 | ❌ | ✅ 可与 Safety_MAS 集成 |
| 统一返回格式 | ❌ | ✅ `WorkflowResult` |

### 4.1 消息钩子示例

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

### 4.2 与 Safety_MAS 集成

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

## 5. 快速参考

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

---

## 参考资料

- [AG2 GroupChat 文档](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/groupchat/)
- [AG2 FSM GroupChat](https://docs.ag2.ai/0.8.7/docs/use-cases/notebooks/notebooks/agentchat_groupchat_finite_state_machine/)
- [AG2 StateFlow](https://docs.ag2.ai/latest/docs/blog/2024/02/29/StateFlow/)

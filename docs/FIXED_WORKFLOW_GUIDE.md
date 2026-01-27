# AG2 固定 Workflow 实现指南

## 1. 什么是固定 Workflow

### 1.1 定义

**固定 Workflow** 是指多智能体系统中，agent 之间的转换路径是预先确定的，不依赖 LLM 的动态判断。

**核心特征：**
- ✅ **边的转换是确定性的**：要么是固定顺序，要么通过非 LLM 的条件判断（如检查消息内容、状态变量）
- ✅ **终止条件可以使用 LLM**：允许 LLM 判断任务是否完成
- ❌ **不使用 LLM 选择下一个 speaker**：避免 LLM 在多个可选路径中做选择

### 1.2 固定 Workflow vs 智能群聊

| 特性 | 固定 Workflow | 智能群聊 (Auto) |
|------|--------------|----------------|
| 转换路径 | 预先定义，确定性 | LLM 动态选择 |
| 可预测性 | 高 - 路径固定 | 低 - 依赖 LLM 判断 |
| 适用场景 | 流程明确的任务 | 开放式协作 |
| 成本 | 低 - 减少 LLM 调用 | 高 - 每次转换都需要 LLM |
| 示例 | 审批流程、流水线 | 头脑风暴、自由讨论 |

### 1.3 为什么需要固定 Workflow

1. **可预测性**：确保任务按照预定流程执行
2. **成本控制**：减少不必要的 LLM 调用
3. **安全性**：避免 LLM 做出意外的路径选择
4. **可测试性**：固定路径更容易测试和验证
5. **合规性**：某些场景（如审批流程）需要严格的流程控制

---

## 2. AG2 中的 Speaker Selection 机制

### 2.1 AG2 的 Speaker Selection 方式

AG2 的 GroupChat 支持多种 speaker selection 方式：

```python
group_chat = GroupChat(
    agents=agents,
    messages=[],
    max_round=10,
    speaker_selection_method=...,  # 关键参数
)
```

**可选值：**

| 方式 | 说明 | 是否固定 | LLM 参与 |
|------|------|---------|---------|
| `"auto"` | LLM 自动选择下一个 speaker | ❌ | ✅ 每次转换 |
| `"round_robin"` | 按列表顺序轮询 | ✅ | ❌ |
| `"random"` | 随机选择 | ❌ | ❌ |
| `custom_function` | 自定义函数 | ✅ (如果函数确定性) | ❌ |
| `allowed_transitions` + `"auto"` | 限制范围内 LLM 选择 | ⚠️ 部分固定 | ✅ 在允许范围内 |

### 2.2 常见误区

**误区 1：使用邻接表就是固定 workflow**

```python
# ❌ 这不是完全固定的 workflow
allowed_transitions = {
    coordinator: [searcher, analyzer, summarizer],  # 3 个选择
}
group_chat = GroupChat(
    agents=agents,
    allowed_or_disallowed_speaker_transitions=allowed_transitions,
    speaker_transitions_type="allowed",
    # 默认仍使用 LLM 在允许的范围内选择
)
```

**问题**：虽然限制了可选范围，但 coordinator 之后去哪个 agent，仍由 LLM 判断。

**误区 2：认为没有双向边就是固定的**

邻接表只定义了"允许的转换"，不定义"转换的顺序"。即使没有双向边，LLM 仍可以在允许的范围内自由选择。

---

## 3. 实现固定 Workflow 的方法

### 3.1 方法一：Round Robin（轮询模式）

**适用场景**：所有 agent 地位平等，需要依次轮流发言

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

# 创建 agents
agents = [agent_a, agent_b, agent_c, agent_d]

# 使用 round_robin
group_chat = GroupChat(
    agents=agents,
    messages=[],
    max_round=12,
    speaker_selection_method="round_robin",  # 固定轮询
)

manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
```

**转换路径**：
```
agent_a → agent_b → agent_c → agent_d → agent_a → agent_b → ...
```

**特点**：
- ✅ 完全固定，不依赖 LLM
- ✅ 简单易用
- ❌ 只适合平等协作场景
- ❌ 不适合 hub-and-spoke 模式

**终止条件**：
```python
agent_a = ConversableAgent(
    name="agent_a",
    is_termination_msg=lambda x: "TASK COMPLETE" in x.get("content", "").upper(),
    ...
)
```

---

### 3.2 方法二：自定义状态转换函数（推荐）

**适用场景**：需要复杂的转换逻辑，如 hub-and-spoke、条件分支、循环

#### 3.2.1 基本模式：固定顺序

```python
def fixed_state_transition(last_speaker, groupchat):
    """固定顺序的状态转换：A → B → C → D → 终止"""
    messages = groupchat.messages

    if last_speaker is agent_a:
        return agent_b
    elif last_speaker is agent_b:
        return agent_c
    elif last_speaker is agent_c:
        return agent_d
    elif last_speaker is agent_d:
        return None  # 终止

    return None

group_chat = GroupChat(
    agents=[agent_a, agent_b, agent_c, agent_d],
    messages=[],
    max_round=10,
    speaker_selection_method=fixed_state_transition,  # 使用自定义函数
)
```

**转换路径**：
```
agent_a → agent_b → agent_c → agent_d → (终止)
```

**特点**：
- ✅ 完全固定，确定性转换
- ✅ 不依赖 LLM
- ✅ 代码清晰，易于理解

#### 3.2.2 Hub-and-Spoke 模式

**场景**：中心 coordinator 协调多个专家 agent

```python
def hub_and_spoke_transition(last_speaker, groupchat):
    """Hub-and-Spoke 模式：User → Coordinator → Specialists → Coordinator → User"""
    messages = groupchat.messages

    # 状态追踪（使用 groupchat 的自定义属性）
    if not hasattr(groupchat, '_workflow_state'):
        groupchat._workflow_state = {
            'phase': 'init',  # init, search, analyze, summarize, complete
            'search_done': False,
            'analyze_done': False,
            'summarize_done': False,
        }

    state = groupchat._workflow_state

    # User → Coordinator（开始）
    if last_speaker is user_proxy:
        state['phase'] = 'search'
        return coordinator

    # Coordinator → Specialists（根据阶段）
    elif last_speaker is coordinator:
        if state['phase'] == 'search' and not state['search_done']:
            return searcher
        elif state['phase'] == 'analyze' and not state['analyze_done']:
            return analyzer
        elif state['phase'] == 'summarize' and not state['summarize_done']:
            return summarizer
        elif state['phase'] == 'complete':
            return user_proxy  # 回到 User，触发终止检查
        else:
            return None  # 异常情况，终止

    # Specialists → Coordinator（报告结果）
    elif last_speaker is searcher:
        state['search_done'] = True
        state['phase'] = 'analyze'
        return coordinator

    elif last_speaker is analyzer:
        state['analyze_done'] = True
        state['phase'] = 'summarize'
        return coordinator

    elif last_speaker is summarizer:
        state['summarize_done'] = True
        state['phase'] = 'complete'
        return coordinator

    return None

group_chat = GroupChat(
    agents=[user_proxy, coordinator, searcher, analyzer, summarizer],
    messages=[],
    max_round=30,
    speaker_selection_method=hub_and_spoke_transition,
)
```

**转换路径**：
```
User → Coordinator → Searcher → Coordinator → Analyzer → Coordinator → Summarizer → Coordinator → User → (终止)
```

**特点**：
- ✅ 严格固定的顺序
- ✅ 使用状态变量追踪进度
- ✅ 不依赖 LLM 选择路径
- ✅ 适合复杂的工作流

#### 3.2.3 条件分支模式

**场景**：根据消息内容（非 LLM 判断）决定路径

```python
def conditional_transition(last_speaker, groupchat):
    """条件分支：根据消息内容决定路径"""
    messages = groupchat.messages

    if last_speaker is user_proxy:
        return coordinator

    elif last_speaker is coordinator:
        # 检查最后一条消息的内容（非 LLM 判断）
        last_msg = messages[-1].get("content", "") if messages else ""

        if "需要搜索" in last_msg or "search" in last_msg.lower():
            return searcher
        elif "需要分析" in last_msg or "analyze" in last_msg.lower():
            return analyzer
        elif "需要总结" in last_msg or "summarize" in last_msg.lower():
            return summarizer
        else:
            return None  # 无法判断，终止

    elif last_speaker in [searcher, analyzer, summarizer]:
        return coordinator  # 所有专家都回到 coordinator

    return None

group_chat = GroupChat(
    agents=[user_proxy, coordinator, searcher, analyzer, summarizer],
    messages=[],
    max_round=30,
    speaker_selection_method=conditional_transition,
)
```

**特点**：
- ✅ 根据消息内容决定路径
- ✅ 使用字符串匹配，不依赖 LLM
- ⚠️ 需要 agent 输出符合约定的关键词

---

### 3.3 方法三：混合模式（邻接表 + 自定义函数）

**场景**：使用邻接表作为安全约束，自定义函数实现确定性选择

```python
# 定义邻接表（作为安全约束）
allowed_transitions = {
    user_proxy: [coordinator],
    coordinator: [searcher, analyzer, summarizer, user_proxy],
    searcher: [coordinator],
    analyzer: [coordinator],
    summarizer: [coordinator],
}

def safe_hub_and_spoke_transition(last_speaker, groupchat):
    """带安全检查的 hub-and-spoke 转换"""
    # ... (与 3.2.2 相同的逻辑)
    next_speaker = ...  # 确定下一个 speaker

    # 安全检查：确保转换是允许的
    if next_speaker and next_speaker not in allowed_transitions.get(last_speaker, []):
        print(f"[WARNING] Illegal transition: {last_speaker.name} → {next_speaker.name}")
        return None

    return next_speaker

group_chat = GroupChat(
    agents=[user_proxy, coordinator, searcher, analyzer, summarizer],
    messages=[],
    max_round=30,
    speaker_selection_method=safe_hub_and_spoke_transition,
    # 注意：不使用 allowed_or_disallowed_speaker_transitions
    # 因为我们在自定义函数中手动检查
)
```

**特点**：
- ✅ 双重保护：自定义逻辑 + 邻接表检查
- ✅ 更安全，防止逻辑错误
- ⚠️ 代码稍复杂

---

## 4. 终止条件的设置

### 4.1 使用 is_termination_msg（推荐）

**允许 LLM 判断任务完成**：

```python
user_proxy = ConversableAgent(
    name="User",
    system_message="...",
    llm_config=llm_config,
    is_termination_msg=lambda x: "RESEARCH COMPLETE" in x.get("content", "").upper() if x else False,
)
```

**工作原理**：
1. Coordinator 完成任务后，回到 User 并说 "RESEARCH COMPLETE"
2. User 的 `is_termination_msg` 检测到关键词
3. 对话终止

**特点**：
- ✅ 允许 LLM 判断任务是否完成
- ✅ 灵活，可以检测复杂条件
- ✅ 符合"只有终止条件可以使用 LLM"的要求

### 4.2 在 system_message 中明确指令

```python
coordinator = ConversableAgent(
    name="Coordinator",
    system_message="""...
When ALL tasks are complete, report back to the User with "RESEARCH COMPLETE" to end the conversation.

IMPORTANT: You MUST say "RESEARCH COMPLETE" when done.
""",
    ...
)
```

### 4.3 max_round 作为保险

```python
group_chat = GroupChat(
    agents=agents,
    max_round=30,  # 防止无限循环
    ...
)
```

---

## 5. 完整示例

### 5.1 研究助手系统（Hub-and-Spoke）

```python
from autogen import ConversableAgent, GroupChat, GroupChatManager

def create_fixed_research_mas():
    """创建固定 workflow 的研究助手系统"""

    # 创建 agents
    user_proxy = ConversableAgent(
        name="User",
        system_message="You represent the user.",
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "RESEARCH COMPLETE" in x.get("content", "").upper() if x else False,
    )

    coordinator = ConversableAgent(
        name="Coordinator",
        system_message="""You are the Coordinator.

Your workflow:
1. Receive task from User
2. Delegate to Searcher for paper search
3. Delegate to Analyzer for paper analysis
4. Delegate to Summarizer for summary creation
5. Report back to User with "RESEARCH COMPLETE"

Follow this exact sequence.""",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    searcher = ConversableAgent(
        name="Searcher",
        system_message="You search for papers. Report results to Coordinator.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    analyzer = ConversableAgent(
        name="Analyzer",
        system_message="You analyze papers. Report findings to Coordinator.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    summarizer = ConversableAgent(
        name="Summarizer",
        system_message="You create summaries. Report completion to Coordinator.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # 定义固定的状态转换函数
    def fixed_workflow_transition(last_speaker, groupchat):
        """固定的 Hub-and-Spoke workflow"""
        if not hasattr(groupchat, '_state'):
            groupchat._state = {'phase': 0}  # 0: init, 1: search, 2: analyze, 3: summarize, 4: complete

        state = groupchat._state

        if last_speaker is user_proxy:
            state['phase'] = 1
            return coordinator

        elif last_speaker is coordinator:
            if state['phase'] == 1:
                return searcher
            elif state['phase'] == 2:
                return analyzer
            elif state['phase'] == 3:
                return summarizer
            elif state['phase'] == 4:
                return user_proxy  # 触发终止检查
            else:
                return None

        elif last_speaker is searcher:
            state['phase'] = 2
            return coordinator

        elif last_speaker is analyzer:
            state['phase'] = 3
            return coordinator

        elif last_speaker is summarizer:
            state['phase'] = 4
            return coordinator

        return None

    # 创建 GroupChat
    agents = [user_proxy, coordinator, searcher, analyzer, summarizer]
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=30,
        speaker_selection_method=fixed_workflow_transition,  # 使用自定义函数
    )

    manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)

    return agents, group_chat, manager, user_proxy

# 使用
agents, group_chat, manager, user_proxy = create_fixed_research_mas()
user_proxy.initiate_chat(
    manager,
    message="Research multi-agent system safety risks."
)
```

**转换路径可视化**：
```
User → Coordinator → Searcher → Coordinator → Analyzer → Coordinator → Summarizer → Coordinator → User → (终止)
```

**特点**：
- ✅ 完全固定的转换顺序
- ✅ 使用状态变量追踪进度
- ✅ 不依赖 LLM 选择路径
- ✅ 只有终止条件使用 LLM 判断

---

## 6. 最佳实践

### 6.1 状态管理

**使用 groupchat 的自定义属性**：
```python
if not hasattr(groupchat, '_workflow_state'):
    groupchat._workflow_state = {'phase': 'init', 'step': 0}
```

**或使用闭包**：
```python
def create_transition_function():
    state = {'phase': 'init'}

    def transition(last_speaker, groupchat):
        # 使用 state
        ...

    return transition

transition_func = create_transition_function()
```

### 6.2 调试和日志

```python
def fixed_workflow_transition(last_speaker, groupchat):
    next_speaker = ...  # 确定下一个 speaker

    # 添加日志
    print(f"[WORKFLOW] {last_speaker.name} → {next_speaker.name if next_speaker else 'TERMINATE'}")

    return next_speaker
```

### 6.3 错误处理

```python
def safe_transition(last_speaker, groupchat):
    try:
        next_speaker = ...  # 转换逻辑

        # 验证 next_speaker 是否有效
        if next_speaker and next_speaker not in groupchat.agents:
            print(f"[ERROR] Invalid speaker: {next_speaker}")
            return None

        return next_speaker
    except Exception as e:
        print(f"[ERROR] Transition failed: {e}")
        return None
```

### 6.4 可测试性

```python
def test_workflow_transitions():
    """测试工作流转换逻辑"""
    # 创建 mock groupchat
    class MockGroupChat:
        def __init__(self):
            self.messages = []
            self.agents = [user_proxy, coordinator, searcher]

    groupchat = MockGroupChat()

    # 测试转换
    assert fixed_workflow_transition(user_proxy, groupchat) == coordinator
    assert fixed_workflow_transition(coordinator, groupchat) == searcher
    # ...
```

---

## 7. 对比总结

### 7.1 三种方法对比

| 方法 | 固定性 | 灵活性 | 复杂度 | 适用场景 |
|------|--------|--------|--------|---------|
| Round Robin | ✅✅✅ | ❌ | 低 | 平等协作 |
| 自定义函数 | ✅✅✅ | ✅✅✅ | 中 | Hub-and-Spoke、条件分支 |
| 邻接表 + Auto | ⚠️ | ✅✅ | 低 | 限制范围的智能选择 |

### 7.2 何时使用固定 Workflow

**适合使用固定 Workflow**：
- ✅ 流程明确，步骤固定
- ✅ 需要严格的流程控制
- ✅ 成本敏感，需要减少 LLM 调用
- ✅ 安全性要求高
- ✅ 需要可预测的行为

**不适合使用固定 Workflow**：
- ❌ 开放式协作，需要灵活讨论
- ❌ 无法预先定义流程
- ❌ 需要 agent 自主决策

---

## 8. 常见问题

### Q1: 邻接表 + "auto" 算固定 workflow 吗？

**A**: 不算。虽然限制了可选范围，但在允许的范围内，LLM 仍会动态选择下一个 speaker。

### Q2: 如何确保 workflow 真正固定？

**A**: 使用自定义函数，并在函数中使用确定性逻辑（状态变量、字符串匹配等），不调用 LLM。

### Q3: 终止条件可以使用 LLM 吗？

**A**: 可以。终止条件通常需要 LLM 判断任务是否完成，这是合理的。使用 `is_termination_msg` 实现。

### Q4: 如何调试固定 workflow？

**A**:
1. 在自定义函数中添加日志
2. 打印状态变量
3. 使用 `max_round` 防止无限循环
4. 编写单元测试

### Q5: 固定 workflow 的性能如何？

**A**: 更好。因为不需要 LLM 选择下一个 speaker，减少了 LLM 调用次数和延迟。

---

## 9. 参考资料

- [AG2 GroupChat 文档](https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/groupchat/)
- [AG2 FSM GroupChat](https://docs.ag2.ai/0.8.7/docs/use-cases/notebooks/notebooks/agentchat_groupchat_finite_state_machine/)
- [AG2_WORKFLOW_GUIDE.md](../src/level1_framework/AG2_WORKFLOW_GUIDE.md)

---

## 10. 总结

**固定 Workflow 的核心原则**：
1. ✅ 使用自定义函数实现确定性转换
2. ✅ 使用状态变量追踪进度
3. ✅ 不依赖 LLM 选择路径
4. ✅ 只有终止条件可以使用 LLM
5. ✅ 添加日志和错误处理

**推荐方案**：
- 简单场景：Round Robin
- 复杂场景：自定义状态转换函数（Hub-and-Spoke）
- 安全关键：混合模式（邻接表 + 自定义函数）

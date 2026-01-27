# AG2 GroupChat 消息格式机制

本文档记录 AG2 (AutoGen) 框架中 GroupChat 模式下的消息存储和传递机制。

## 核心发现

通过 `step0_trace_fixed_workflow_messages.py` 脚本追踪，发现 AG2 的消息上下文机制如下：

### 1. 消息存储位置

```python
agent._oai_messages[sender]  # sender 在 GroupChat 中始终是 chat_manager
```

每个 agent 维护一个以 sender 为 key 的消息字典。在 GroupChat 场景下，所有消息都来自 `chat_manager`，因此所有历史消息都存储在 `_oai_messages[chat_manager]` 中。

### 2. Role 分配规则

AG2 将消息转换为 OpenAI Chat API 格式时，按以下规则分配 `role`：

| 消息来源 | 当前 Agent 看到的 role |
|---------|----------------------|
| **自己之前发的消息** | `assistant` |
| **其他任何 agent 发的消息** | `user` |

### 3. 实际消息格式示例

假设对话流程: `User -> Coordinator -> Worker -> Coordinator`

**Coordinator 第二次被调用时的上下文：**

```json
[
  {"role": "user", "name": "User", "content": "任务描述..."},
  {"role": "assistant", "name": "Coordinator", "content": "我之前的回复..."},
  {"role": "user", "name": "Worker", "content": "Worker的回复..."}
]
```

**Worker 被调用时的上下文：**

```json
[
  {"role": "user", "name": "User", "content": "任务描述..."},
  {"role": "user", "name": "Coordinator", "content": "Coordinator的回复..."}
]
```

注意：Coordinator 的消息对 Worker 来说是 `role: "user"`，但对 Coordinator 自己来说是 `role: "assistant"`。

### 4. 上下文累积

GroupChat 中的消息会持续累积：

```
Round 1: Coordinator 看到 1 条消息 (User 的任务)
Round 2: Worker 看到 2 条消息 (User + Coordinator)
Round 3: Coordinator 看到 3 条消息 (User + 自己 + Worker)
Round 4: User 看到 4 条消息 (完整历史)
```

## 消息广播机制

GroupChat 使用**广播模式**：

```
                    ┌──────────────┐
                    │ chat_manager │
                    └──────┬───────┘
                           │ 广播给所有 agents
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
        ┌──────┐     ┌───────────┐    ┌────────┐
        │ User │     │Coordinator│    │ Worker │
        └──────┘     └───────────┘    └────────┘
```

- 每条消息都发送给所有参与者
- 但只有被 `speaker_selection` 选中的 agent 才会调用 `generate_reply()`
- 消息的"接收"是广播的，"发言权"由 speaker selection 控制

## 安全研究意义

### 潜在攻击向量

1. **上下文注入攻击**
   - 恶意 agent 的输出直接进入其他 agent 的 `user` 消息
   - 可以在 content 中伪造格式来混淆，如 `"[assistant] 我之前说过..."`

2. **信息泄露**
   - 每个 agent 都能看到完整的对话历史
   - 即使某些消息不是发给它的

3. **角色混淆**
   - 所有非自己的消息都是 `role: "user"`
   - LLM 可能难以区分不同 agent 的权限级别

### 防御考虑

Level 2/3 安全层可以在以下位置进行拦截：

1. **消息发送前** - 检查 agent 输出是否包含恶意内容
2. **消息接收后** - 过滤或标记可疑的上下文消息
3. **generate_reply 前** - 对构造的 messages 列表进行安全检查

## 验证脚本

使用以下脚本可以追踪消息流：

```bash
python examples/full_demo/step0_trace_fixed_workflow_messages.py
```

输出格式：

```
======================================================================
>>> AGENT: Coordinator  (call #2)
======================================================================
Sender: chat_manager
Internal context (_oai_messages[chat_manager]): 3 messages
    [0] [user] User: 任务描述...
    [1] [assistant] Coordinator: 我之前的回复...
    [2] [user] Worker: Worker的回复...
----------------------------------------------------------------------
Reply: 最终回复...
======================================================================
```

## 参考

- AG2 源码: `autogen/agentchat/conversable_agent.py`
- `_oai_messages` 数据结构
- `generate_reply()` 方法

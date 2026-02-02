# 修改方案：跳过 chat_manager，显示真实接收方

## 问题描述

在当前实现中，所有消息的 `to_agent` 字段都显示为 `chat_manager`，因为在 AG2 的 GroupChat 模式下：

1. 所有 agent 发送消息时，实际接收者（recipient）是 `GroupChatManager`
2. `GroupChatManager` 负责路由消息到真正的目标 agent
3. 我们的消息钩子捕获的是 `agent.send()` 层面的消息，此时 `recipient` 就是 `chat_manager`

**示例日志**:
```json
{
  "from_agent": "Searcher",
  "to_agent": "chat_manager",  // ❌ 这是内部实现细节
  "content": "..."
}
```

**期望日志**:
```json
{
  "from_agent": "Searcher",
  "to_agent": "Analyzer",  // ✅ 真实的目标 agent
  "content": "..."
}
```

---

## 根本原因分析

### 1. AG2 GroupChat 架构

```
Agent A --send()--> GroupChatManager --_process_received_message()--> Agent B
         (这里被钩子捕获)                  (实际路由在这里发生)
```

在 `src/level1_framework/ag2_wrapper.py` 的 `_wrap_agent_send` 方法中：

```python
def send_wrapper(message, recipient, request_reply=None, silent=False):
    hook_msg = {
        "from": agent_name,
        "to": recipient.name,  # ← 这里的 recipient 是 GroupChatManager
        "content": msg_dict.get("content", ""),
        # ...
    }
```

### 2. GroupChatManager 的内部逻辑

GroupChatManager 选择下一个 speaker 的逻辑在：
- `select_speaker()` 方法（可能基于 LLM、规则或 speaker_transitions）
- 在 `_process_received_message()` 中实际发送给选中的 agent

问题是，我们的钩子在 `select_speaker()` **之前**就已经被调用了。

---

## 解决方案

### 方案 1：钩住 GroupChatManager 的 select_speaker 逻辑 ⭐ 推荐

**核心思路**：不仅钩住 agent 的 `send()`，还钩住 `GroupChatManager` 的内部路由逻辑，记录真实的下一个 speaker。

#### 实现步骤

**Step 1: 包装 GroupChatManager 的关键方法**

在 `ag2_wrapper.py` 的 `_setup_message_interception` 方法中添加：

```python
def _setup_message_interception(self):
    """Set up message interception for all agents."""
    # Existing: Wrap all agent send methods
    for agent_name, agent in self._agents.items():
        self._wrap_agent_send(agent, agent_name)

    # NEW: Wrap GroupChatManager if exists
    if self._manager:
        self._wrap_manager_routing()

def _wrap_manager_routing(self):
    """Wrap GroupChatManager to capture actual recipient selection."""
    if not hasattr(self._manager, '_original_run_chat'):
        original_run_chat = self._manager.run_chat
        mas_ref = self  # Capture self reference

        def run_chat_wrapper(messages=None, sender=None, config=None):
            """Wrapper for GroupChatManager.run_chat to track next speaker."""
            result = original_run_chat(messages=messages, sender=sender, config=config)

            # After run_chat completes, the manager has selected the next speaker
            # We can now update the last message in history with the actual recipient
            if hasattr(self._manager, 'groupchat') and hasattr(self._manager.groupchat, 'messages'):
                last_message = self._manager.groupchat.messages[-1] if self._manager.groupchat.messages else None

                if last_message and isinstance(last_message, dict):
                    # Try to get the actual speaker name from the message
                    actual_recipient = last_message.get('name', None)

                    # Update the last entry in our message history
                    if mas_ref._message_history and actual_recipient:
                        last_logged = mas_ref._message_history[-1]
                        if last_logged.get('to') == 'chat_manager':
                            # Found a message that was sent to chat_manager
                            # Update it with the actual recipient
                            last_logged['to'] = actual_recipient
                            last_logged['to_agent_resolved'] = True

            return result

        self._manager.run_chat = run_chat_wrapper
        self._manager._original_run_chat = original_run_chat
```

**Step 2: 添加上下文追踪**

维护一个"下一个 speaker"的上下文，在消息记录时使用：

```python
class AG2MAS(BaseMAS):
    def __init__(self, agents: List[ConversableAgent], mode: str = "group_chat"):
        # ... existing code ...
        self._next_speaker_cache: Dict[float, str] = {}  # timestamp -> next_speaker_name
        self._last_message_timestamp: Optional[float] = None

    def _wrap_agent_send(self, agent: ConversableAgent, agent_name: str):
        """Enhanced version with next speaker prediction."""
        original_send = agent.send
        mas_ref = self

        def send_wrapper(message, recipient, request_reply=None, silent=False):
            # ... existing normalization code ...

            # Try to predict next speaker if we're in GroupChat mode
            actual_recipient = recipient.name if hasattr(recipient, 'name') else str(recipient)

            if actual_recipient == "chat_manager" and mas_ref._manager:
                # Attempt to predict next speaker based on speaker_transitions
                predicted_next = mas_ref._predict_next_speaker(agent_name, msg_dict)
                if predicted_next:
                    actual_recipient = predicted_next

            hook_msg = {
                "from": agent_name,
                "to": actual_recipient,  # Use predicted or actual recipient
                "to_is_manager": (recipient.name == "chat_manager") if hasattr(recipient, 'name') else False,
                "content": msg_dict.get("content", ""),
                # ... rest of the fields ...
            }

            # ... rest of the method ...

            # Log with resolved recipient
            mas_ref._message_history.append({
                "from": agent_name,
                "to": actual_recipient,
                "content": modified_hook_msg["content"],
                "timestamp": time.time(),
                "via_manager": hook_msg["to_is_manager"]
            })

            return original_send(modified_message, recipient, request_reply, silent)

        agent.send = send_wrapper

    def _predict_next_speaker(self, current_speaker: str, message: dict) -> Optional[str]:
        """Predict next speaker based on GroupChat configuration.

        Args:
            current_speaker: Name of the agent sending the message
            message: Message dict

        Returns:
            Predicted next speaker name, or None if cannot predict
        """
        if not self._group_chat:
            return None

        # Method 1: Check speaker_transitions (if defined)
        if hasattr(self._group_chat, 'allowed_or_disallowed_speaker_transitions'):
            transitions = self._group_chat.allowed_or_disallowed_speaker_transitions
            if transitions and isinstance(transitions, dict):
                # Find the current agent object
                current_agent = self._agents.get(current_speaker)
                if current_agent in transitions:
                    allowed_next = transitions[current_agent]
                    if allowed_next and len(allowed_next) == 1:
                        # If there's only one allowed next speaker, use it
                        return allowed_next[0].name if hasattr(allowed_next[0], 'name') else None

        # Method 2: Check if there's a pattern in recent messages
        if len(self._message_history) >= 2:
            # Look at the last few messages to detect a pattern
            recent_senders = [msg['from'] for msg in self._message_history[-3:]]
            # Simple heuristic: if there's a repeating A->B->A pattern, predict B
            if len(recent_senders) >= 2 and recent_senders[-1] != recent_senders[-2]:
                return recent_senders[-1]  # Likely to alternate

        # Method 3: Cannot predict - return None
        return None
```

**优点**:
- ✅ 在钩子层面就获取真实接收方
- ✅ 对现有代码改动最小
- ✅ 支持 speaker_transitions 配置
- ✅ 即使预测失败，也不会崩溃（降级为 chat_manager）

**缺点**:
- ⚠️ 预测可能不准确（特别是 LLM-based select_speaker）
- ⚠️ 需要维护额外的状态

---

### 方案 2：后处理消息历史 ⚡ 最简单

**核心思路**：不修改钩子逻辑，而是在生成日志/报告时，基于消息序列后处理 `to_agent` 字段。

#### 实现步骤

**Step 1: 添加后处理工具函数**

在 `src/utils/message_utils.py`（新建文件）:

```python
"""Message processing utilities for resolving chat_manager recipients."""

from typing import List, Dict, Optional


def resolve_chat_manager_recipients(messages: List[Dict]) -> List[Dict]:
    """Resolve 'chat_manager' recipients to actual next speakers.

    Args:
        messages: List of message dicts with 'from', 'to', 'content' fields

    Returns:
        New list with resolved 'to' fields
    """
    resolved = []

    for i, msg in enumerate(messages):
        new_msg = msg.copy()

        # If recipient is chat_manager, look at the next message to find actual recipient
        if msg.get('to') == 'chat_manager' and i + 1 < len(messages):
            next_msg = messages[i + 1]
            # The next message's sender is the actual recipient of this message
            if next_msg.get('from') != msg.get('from'):  # Different speaker
                new_msg['to'] = next_msg['from']
                new_msg['to_resolved'] = True
                new_msg['to_original'] = 'chat_manager'

        resolved.append(new_msg)

    return resolved


def resolve_message_flows(messages: List[Dict]) -> List[Dict]:
    """Advanced resolution with conversation flow analysis.

    Args:
        messages: List of message dicts

    Returns:
        Messages with resolved recipients and flow annotations
    """
    resolved = []
    speaker_sequence = []

    for i, msg in enumerate(messages):
        new_msg = msg.copy()
        from_agent = msg.get('from')
        to_agent = msg.get('to')

        # Track speaker sequence
        if from_agent not in speaker_sequence or speaker_sequence[-1] != from_agent:
            speaker_sequence.append(from_agent)

        # Resolve chat_manager
        if to_agent == 'chat_manager':
            # Strategy 1: Look ahead to next speaker
            next_speaker = _find_next_speaker(messages, i)
            if next_speaker and next_speaker != from_agent:
                new_msg['to'] = next_speaker
                new_msg['to_resolved_method'] = 'lookahead'

            # Strategy 2: Pattern detection (e.g., round-robin)
            elif len(speaker_sequence) >= 2:
                # Detect repeating patterns
                pattern_next = _detect_pattern_next_speaker(speaker_sequence, from_agent)
                if pattern_next:
                    new_msg['to'] = pattern_next
                    new_msg['to_resolved_method'] = 'pattern'

            # Strategy 3: Keep as chat_manager but mark as unresolved
            else:
                new_msg['to_resolved_method'] = 'unresolved'

            new_msg['to_original'] = 'chat_manager'

        resolved.append(new_msg)

    return resolved


def _find_next_speaker(messages: List[Dict], current_idx: int) -> Optional[str]:
    """Find the next speaker after current message."""
    for i in range(current_idx + 1, len(messages)):
        next_from = messages[i].get('from')
        current_from = messages[current_idx].get('from')
        if next_from and next_from != current_from:
            return next_from
    return None


def _detect_pattern_next_speaker(speaker_sequence: List[str], current_speaker: str) -> Optional[str]:
    """Detect repeating pattern and predict next speaker."""
    if len(speaker_sequence) < 3:
        return None

    # Check for simple alternation (A->B->A->B)
    if len(set(speaker_sequence[-3:])) == 2:
        # Alternating pattern
        for speaker in speaker_sequence[-3:]:
            if speaker != current_speaker:
                return speaker

    # Check for round-robin (A->B->C->A->B->C)
    if len(speaker_sequence) >= 4:
        # Find the cycle length
        for cycle_len in range(2, len(speaker_sequence) // 2 + 1):
            if speaker_sequence[-cycle_len:] == speaker_sequence[-2*cycle_len:-cycle_len]:
                # Found a repeating pattern
                try:
                    current_idx = speaker_sequence[-cycle_len:].index(current_speaker)
                    next_idx = (current_idx + 1) % cycle_len
                    return speaker_sequence[-cycle_len:][next_idx]
                except ValueError:
                    continue

    return None
```

**Step 2: 在日志生成时应用后处理**

修改 `src/level3_safety/console_logger.py`（或相关日志模块）:

```python
from src.utils.message_utils import resolve_chat_manager_recipients

class Level3ConsoleLogger:
    # ... existing code ...

    def end_session(self, success: bool = True, error: Optional[str] = None) -> Optional[Path]:
        """End session and save to JSON with resolved recipients."""
        if not self._session_data:
            return None

        # ... existing code ...

        # NEW: Resolve chat_manager recipients before saving
        if "messages" in self._session_data:
            self._session_data["messages"] = resolve_chat_manager_recipients(
                self._session_data["messages"]
            )

        # Save to JSON
        # ... rest of the method ...
```

**优点**:
- ✅ 实现简单，不修改核心钩子逻辑
- ✅ 可以应用于已有的日志文件（后处理脚本）
- ✅ 容易测试和调试
- ✅ 不影响运行时性能

**缺点**:
- ⚠️ 只在最终日志中解决，运行时仍显示 chat_manager
- ⚠️ 依赖消息序列完整性

---

### 方案 3：修改 GroupChat 的 speaker_selection 回调 🔧 最准确

**核心思路**：利用 AG2 GroupChat 的 `speaker_selection_method` 参数，注入自定义逻辑来捕获真实的 speaker 选择。

#### 实现步骤

**Step 1: 自定义 speaker selection function**

```python
class AG2MAS(BaseMAS):
    def __init__(self, agents: List[ConversableAgent], mode: str = "group_chat"):
        # ... existing code ...
        self._next_speaker_map: Dict[str, str] = {}  # from_agent -> next_agent

        if mode == "group_chat" and len(agents) > 2:
            # Create custom speaker selection that tracks choices
            self._group_chat = GroupChat(
                agents=agents,
                messages=[],
                max_round=10,
                speaker_selection_method=self._create_tracking_speaker_selector()
            )

    def _create_tracking_speaker_selector(self):
        """Create a speaker selector that tracks selections."""
        mas_ref = self

        # Get the default/original selector
        original_selector = "auto"  # or the configured one

        def tracking_selector(last_speaker, groupchat):
            """Wrapper around speaker selection that tracks the result."""
            # Call original selector logic
            if callable(original_selector):
                next_speaker = original_selector(last_speaker, groupchat)
            else:
                # Use GroupChat's default auto selection
                next_speaker = groupchat.select_speaker(last_speaker, groupchat.agents)

            # Track the selection
            last_name = last_speaker.name if hasattr(last_speaker, 'name') else str(last_speaker)
            next_name = next_speaker.name if hasattr(next_speaker, 'name') else str(next_speaker)

            mas_ref._next_speaker_map[last_name] = next_name

            # Also update the last message in history if it was sent to chat_manager
            if mas_ref._message_history:
                last_msg = mas_ref._message_history[-1]
                if last_msg.get('to') == 'chat_manager' and last_msg.get('from') == last_name:
                    last_msg['to'] = next_name
                    last_msg['to_resolved'] = True

            return next_speaker

        return tracking_selector
```

**Step 2: 在消息钩子中使用 next_speaker_map**

```python
def _wrap_agent_send(self, agent: ConversableAgent, agent_name: str):
    """Enhanced version using next_speaker_map."""
    original_send = agent.send
    mas_ref = self

    def send_wrapper(message, recipient, request_reply=None, silent=False):
        # ... existing normalization code ...

        # Determine actual recipient
        recipient_name = recipient.name if hasattr(recipient, 'name') else str(recipient)

        if recipient_name == "chat_manager":
            # Check if we have a tracked next speaker
            tracked_next = mas_ref._next_speaker_map.get(agent_name)
            if tracked_next:
                recipient_name = tracked_next

        hook_msg = {
            "from": agent_name,
            "to": recipient_name,
            "content": msg_dict.get("content", ""),
            # ...
        }

        # ... rest of the method ...
```

**优点**:
- ✅ 最准确，直接使用 GroupChat 的 speaker selection 结果
- ✅ 支持任何类型的 speaker selection（LLM、规则、自定义）
- ✅ 实时更新，无需后处理

**缺点**:
- ⚠️ 修改较多，需要深度集成 GroupChat
- ⚠️ 可能与 AG2 版本更新不兼容
- ⚠️ 依赖 GroupChat 内部 API

---

## 推荐方案组合 🎯

**最佳实践：方案 1 + 方案 2 组合**

1. **运行时使用方案 1**：尽可能在钩子层面预测/解析真实接收方
   - 使用 speaker_transitions 信息
   - 使用消息模式推断

2. **后处理使用方案 2**：在生成最终报告时，再次解析确保准确性
   - 处理方案 1 可能的遗漏
   - 提供后处理脚本修复历史日志

### 实现优先级

**Phase 1（立即实施）**:
- [ ] 实现方案 2 的后处理函数 `resolve_chat_manager_recipients()`
- [ ] 在 `end_session()` 中应用后处理
- [ ] 编写单元测试验证后处理逻辑

**Phase 2（短期）**:
- [ ] 实现方案 1 的 `_predict_next_speaker()` 基础版本
- [ ] 支持 speaker_transitions 查询
- [ ] 添加简单的模式检测（alternation, round-robin）

**Phase 3（长期优化）**:
- [ ] 考虑方案 3 的 speaker_selection 钩子（如果需要）
- [ ] 优化预测算法（机器学习？）
- [ ] 添加配置选项：是否显示 via_manager 标记

---

## 测试验证

### 测试用例 1：固定 speaker_transitions

```python
# Create a MAS with fixed speaker transitions
agents = [AgentA, AgentB, AgentC]
transitions = {
    AgentA: [AgentB],
    AgentB: [AgentC],
    AgentC: [AgentA]
}
group_chat = GroupChat(
    agents=agents,
    allowed_or_disallowed_speaker_transitions=transitions
)

# Expected: A -> B, B -> C, C -> A (no chat_manager in logs)
```

### 测试用例 2：Round-robin pattern

```python
# Let GroupChat auto-select in round-robin
# After 2-3 rounds, pattern should be detected
# Expected: Logs show predicted next speaker, not chat_manager
```

### 测试用例 3：后处理验证

```python
from src.utils.message_utils import resolve_chat_manager_recipients

messages = [
    {"from": "A", "to": "chat_manager", "content": "Hello"},
    {"from": "B", "to": "chat_manager", "content": "Hi"},
    {"from": "C", "to": "chat_manager", "content": "Hey"}
]

resolved = resolve_chat_manager_recipients(messages)

assert resolved[0]["to"] == "B"  # A's message goes to B (next speaker)
assert resolved[1]["to"] == "C"  # B's message goes to C
```

---

## 配置选项

在 `config.yaml` 中添加配置：

```yaml
level1_framework:
  ag2_wrapper:
    resolve_manager_recipients: true  # 启用真实接收方解析
    resolution_method: "auto"  # auto, predict, lookahead, none
    show_via_manager_tag: false  # 是否显示 via_manager 标记
    fallback_to_manager: true  # 无法解析时是否保留 chat_manager
```

---

## 向后兼容

为了保持向后兼容，可以添加一个标记字段：

```json
{
  "from_agent": "Searcher",
  "to_agent": "Analyzer",
  "to_agent_resolved": true,
  "to_agent_original": "chat_manager",
  "content": "..."
}
```

这样：
- 新版本显示 `to_agent = "Analyzer"`
- 如果需要调试，仍可查看 `to_agent_original = "chat_manager"`

---

## 总结

| 方案 | 准确性 | 实现难度 | 性能影响 | 推荐度 |
|------|--------|----------|----------|--------|
| 方案 1：预测 + 钩子增强 | ⭐⭐⭐⭐ | 中 | 低 | ⭐⭐⭐⭐⭐ |
| 方案 2：后处理 | ⭐⭐⭐⭐⭐ | 低 | 无 | ⭐⭐⭐⭐⭐ |
| 方案 3：speaker_selection 钩子 | ⭐⭐⭐⭐⭐ | 高 | 低 | ⭐⭐⭐ |

**最终建议**：先实现方案 2（后处理），立即解决日志显示问题；然后逐步实现方案 1（预测），提升运行时准确性。
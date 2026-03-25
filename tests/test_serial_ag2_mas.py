"""
AG2 MAS 固定工作流测试脚本

本脚本展示:
1. AG2 原生支持固定 workflow 的方式 (allowed_or_disallowed_speaker_transitions)
2. AG2MAS 可以直接包装这种固定 workflow 的 MAS (不需要 SerialAG2MAS)

AG2 原生支持固定 workflow 的方式:
- allowed_or_disallowed_speaker_transitions: 直接定义 agent 转换图
- speaker_selection_method: 自定义状态转换函数
- StateFlow: 状态机概念
"""

import yaml
from typing import Dict, Any, List

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2")

from src.level1_framework.ag2_wrapper import AG2MAS
from src.level1_framework.base import WorkflowResult


def load_llm_config() -> Dict[str, Any]:
    """从 config/llm_config.yaml 加载 LLM 配置"""
    with open("config/llm_config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return {
        "config_list": [
            {
                "model": config.get("model", "gpt-4o-mini"),
                "api_key": config.get("api_key"),
                "base_url": config.get("base_url"),
            }
        ],
        "temperature": config.get("temperature", 0),
        "timeout": 120,
    }


# ==============================================================================
# Part 1: AG2 原生固定 workflow - 使用 allowed_or_disallowed_speaker_transitions
# ==============================================================================

def ag2_native_fixed_workflow():
    """
    AG2 原生方式: 使用 allowed_or_disallowed_speaker_transitions 定义固定转换图

    这就是 AG2 原生的 "graph" 表示方法!
    """
    print("=" * 70)
    print("Part 1: AG2 原生固定 workflow (allowed_or_disallowed_speaker_transitions)")
    print("=" * 70)

    llm_config = load_llm_config()

    # 创建 user_proxy (发起者，不参与转换图)
    user_proxy = ConversableAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=lambda x: "APPROVED" in x.get("content", "").upper() if x else False,
    )

    # 创建工作流中的 agents
    writer = ConversableAgent(
        name="writer",
        system_message="你是写作代理。写2-3句话，直接输出内容。",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    editor = ConversableAgent(
        name="editor",
        system_message="你是编辑代理。改进文字后输出: 编辑后: [内容]",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    reviewer = ConversableAgent(
        name="reviewer",
        system_message="你是审核代理。评价后输出: 审核: [评价] APPROVED",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # ========================================
    # 关键: 定义固定的转换图 (这就是 AG2 原生的 graph!)
    # ========================================
    # 串行: user_proxy -> writer -> editor -> reviewer
    allowed_transitions = {
        user_proxy: [writer],           # user_proxy 只能转到 writer
        writer: [editor],               # writer 只能转到 editor
        editor: [reviewer],             # editor 只能转到 reviewer
        reviewer: [],                   # reviewer 是终点
    }

    print("\n定义的转换图 (allowed_or_disallowed_speaker_transitions):")
    print("  user_proxy -> writer -> editor -> reviewer")
    print("\n转换字典:")
    for src, dsts in allowed_transitions.items():
        dst_names = [d.name for d in dsts] if dsts else ["(终点)"]
        print(f"  {src.name} -> {dst_names}")

    # 创建 GroupChat，使用固定转换图
    group_chat = GroupChat(
        agents=[user_proxy, writer, editor, reviewer],
        messages=[],
        max_round=10,
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",  # 使用允许列表模式
        send_introductions=False,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    # 执行
    print("\n--- 执行固定 workflow ---")
    task = "请写一段关于海洋探索的文字"
    print(f"任务: {task}\n")

    chat_result = user_proxy.initiate_chat(
        manager,
        message=task,
        max_turns=10,
    )

    # 打印结果
    print("\n--- 执行结果 ---")
    if chat_result.chat_history:
        for i, msg in enumerate(chat_result.chat_history):
            sender = msg.get("name", msg.get("role", "unknown"))
            content = msg.get("content", "")[:80]
            print(f"  [{i+1}] {sender}: {content}...")

    return group_chat, manager


# ==============================================================================
# Part 2: AG2 原生固定 workflow - 使用自定义 speaker_selection_method
# ==============================================================================

def ag2_native_state_machine():
    """
    AG2 原生方式: 使用 speaker_selection_method 自定义状态转换函数

    这是更灵活的方式，可以根据消息内容动态决定下一个 speaker
    """
    print("\n" + "=" * 70)
    print("Part 2: AG2 原生状态机 (speaker_selection_method)")
    print("=" * 70)

    llm_config = load_llm_config()

    user_proxy = ConversableAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=lambda x: "APPROVED" in x.get("content", "").upper() if x else False,
    )

    writer = ConversableAgent(
        name="writer",
        system_message="你是写作代理。写2-3句话，直接输出内容。",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    editor = ConversableAgent(
        name="editor",
        system_message="你是编辑代理。改进文字后输出: 编辑后: [内容]",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    reviewer = ConversableAgent(
        name="reviewer",
        system_message="你是审核代理。评价后输出: 审核: [评价] APPROVED",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # ========================================
    # 关键: 定义状态转换函数
    # ========================================
    def state_transition(last_speaker, groupchat):
        """自定义状态转换函数 - 串行 workflow"""
        if last_speaker is user_proxy:
            return writer
        elif last_speaker is writer:
            return editor
        elif last_speaker is editor:
            return reviewer
        elif last_speaker is reviewer:
            return None  # 终止
        return None

    print("\n定义的状态转换函数:")
    print("  user_proxy -> writer -> editor -> reviewer -> (终止)")

    group_chat = GroupChat(
        agents=[user_proxy, writer, editor, reviewer],
        messages=[],
        max_round=10,
        speaker_selection_method=state_transition,  # 使用自定义函数
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    print("\n--- 执行状态机 workflow ---")
    task = "请写一段关于星空的文字"
    print(f"任务: {task}\n")

    chat_result = user_proxy.initiate_chat(
        manager,
        message=task,
        max_turns=10,
    )

    print("\n--- 执行结果 ---")
    if chat_result.chat_history:
        for i, msg in enumerate(chat_result.chat_history):
            sender = msg.get("name", msg.get("role", "unknown"))
            content = msg.get("content", "")[:80]
            print(f"  [{i+1}] {sender}: {content}...")

    return group_chat, manager


# ==============================================================================
# Part 3: AG2MAS 直接包装固定 workflow (不需要 SerialAG2MAS)
# ==============================================================================

def ag2mas_wrap_fixed_workflow():
    """
    AG2MAS 可以直接包装 AG2 原生的固定 workflow MAS

    不需要创建 SerialAG2MAS 子类!
    """
    print("\n" + "=" * 70)
    print("Part 3: AG2MAS 直接包装固定 workflow (不需要子类)")
    print("=" * 70)

    llm_config = load_llm_config()

    # 创建 agents
    user_proxy = ConversableAgent(
        name="user_proxy",
        human_input_mode="NEVER",
        llm_config=False,
        is_termination_msg=lambda x: "APPROVED" in x.get("content", "").upper() if x else False,
    )

    writer = ConversableAgent(
        name="writer",
        system_message="你是写作代理。写2-3句话，直接输出内容。",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    editor = ConversableAgent(
        name="editor",
        system_message="你是编辑代理。改进文字后输出: 编辑后: [内容]",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    reviewer = ConversableAgent(
        name="reviewer",
        system_message="你是审核代理。评价后输出: 审核: [评价] APPROVED",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    # 定义转换图
    allowed_transitions = {
        user_proxy: [writer],
        writer: [editor],
        editor: [reviewer],
        reviewer: [],
    }

    # 创建 AG2 原生的固定 workflow GroupChat
    group_chat = GroupChat(
        agents=[user_proxy, writer, editor, reviewer],
        messages=[],
        max_round=10,
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
    )

    # ========================================
    # 关键: 直接用 AG2MAS 包装，不需要子类!
    # ========================================
    mas = AG2MAS(
        agents=[user_proxy, writer, editor, reviewer],
        group_chat=group_chat,
        manager=manager
    )

    print("\n创建 AG2MAS 实例 (直接包装固定 workflow):")
    print(f"  Agents: {[a.name for a in mas.get_agents()]}")
    print(f"  Topology: {mas.get_topology()}")

    # 注册消息钩子 (AG2MAS 的附加价值)
    print("\n--- 注册消息钩子 (AG2MAS 的附加价值) ---")

    def logging_hook(msg: dict) -> dict:
        print(f"  [HOOK] {msg['from']} -> {msg['to']}: {msg['content'][:50]}...")
        return msg

    def safety_hook(msg: dict) -> dict:
        content = msg.get("content", "")
        if "ignore" in content.lower() or "忽略" in content:
            print(f"  [SECURITY] 检测到潜在 prompt injection!")
        return msg

    mas.register_message_hook(logging_hook)
    mas.register_message_hook(safety_hook)

    # 执行
    print("\n--- 执行 workflow (通过 AG2MAS.run_workflow) ---")
    task = "请写一段关于森林的文字"
    print(f"任务: {task}\n")

    result = mas.run_workflow(task, max_round=10)

    print(f"\n--- 结果 ---")
    print(f"成功: {result.success}")
    print(f"输出: {result.output}")
    print(f"消息数: {len(result.messages)}")

    print("\n--- 消息历史 (AG2MAS 记录) ---")
    for i, msg in enumerate(result.messages):
        print(f"  [{i+1}] {msg['from']} -> {msg['to']}: {msg['content'][:60]}...")

    return mas


# ==============================================================================
# Main
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("  AG2 固定 Workflow 测试")
    print("=" * 70)

    # Part 1: AG2 原生 - 转换图
    ag2_native_fixed_workflow()

    # Part 2: AG2 原生 - 状态机
    ag2_native_state_machine()

    # Part 3: AG2MAS 直接包装
    ag2mas_wrap_fixed_workflow()

    # 总结
    print("\n" + "=" * 70)
    print("  总结")
    print("=" * 70)
    print("""
AG2 原生就支持固定 workflow，有两种方式:

1. allowed_or_disallowed_speaker_transitions (转换图)
   - 直接定义 {agent: [可转换的目标agents]} 字典
   - 类似于有向图的邻接表
   - 适合简单的固定路径

2. speaker_selection_method (状态转换函数)
   - 自定义函数，根据 last_speaker 和 groupchat 决定下一个
   - 更灵活，可以根据消息内容动态决策
   - 适合复杂的条件分支

AG2MAS 的价值:
- 不需要 SerialAG2MAS 子类
- AG2MAS 可以直接包装任何 AG2 的 GroupChat (包括固定 workflow)
- 附加价值: 消息钩子、安全检查、消息历史记录、与 Safety_MAS 集成

文档参考:
- FSM GroupChat: https://docs.ag2.ai/latest/docs/user-guide/advanced-concepts/groupchat/groupchat/
- StateFlow: https://docs.ag2.ai/latest/docs/blog/2024/02/29/StateFlow/
""")

"""Step 0: Trace AG2 agent contexts in a fixed workflow.

Goal: Check if the same agent's context accumulates messages across rounds.

Fixed workflow (allowed transitions):
  User -> Coordinator -> Worker -> Coordinator -> User (terminate)

Output format:
  For each agent's generate_reply call, shows:
  - Agent name and call count (e.g., "Coordinator call #2")
  - Full context messages list passed to generate_reply
  - The generated reply

Run:
  python examples/full_demo/step0_trace_fixed_workflow_messages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from autogen import ConversableAgent, GroupChat, GroupChatManager
except ImportError:
    try:
        from pyautogen import ConversableAgent, GroupChat, GroupChatManager
    except ImportError as e:
        raise ImportError("AG2/AutoGen not installed. Install with: pip install ag2") from e

from src.utils.llm_config import get_mas_llm_config


# Track how many times each agent's generate_reply is called
_agent_call_count: dict[str, int] = {}


def _format_message(msg) -> str:
    """Format a single message for display."""
    if isinstance(msg, dict):
        role = msg.get("role", "?")
        name = msg.get("name", "?")
        content = msg.get("content", "")
        # Truncate long content for readability
        if len(content) > 150:
            content = content[:150] + "..."
        # Replace newlines for compact display
        content = content.replace("\n", " ↵ ")
        return f"[{role}] {name}: {content}"
    return str(msg)[:150]


def _format_messages_list(messages) -> str:
    """Format the messages list showing the context."""
    if not messages:
        return "    (empty)"
    lines = []
    for i, msg in enumerate(messages):
        lines.append(f"    [{i}] {_format_message(msg)}")
    return "\n".join(lines)


def install_tracers():
    """Monkey-patch AG2 to log agent contexts from internal chat history."""

    orig_generate_reply = getattr(ConversableAgent, "generate_reply")

    def generate_reply_wrapper(self, messages=None, sender=None, *args, **kwargs):
        # Skip internal agents (speaker selection, etc.)
        if self.name in ("speaker_selection_agent", "checking_agent"):
            return orig_generate_reply(self, messages=messages, sender=sender, *args, **kwargs)

        # Track call count per agent
        if self.name not in _agent_call_count:
            _agent_call_count[self.name] = 0
        _agent_call_count[self.name] += 1
        call_num = _agent_call_count[self.name]

        # Print header
        print("\n" + "=" * 70)
        print(f">>> AGENT: {self.name}  (call #{call_num})")
        print("=" * 70)

        # Try to get the REAL context from agent's internal chat history
        # AG2 stores chat history in self._oai_messages[sender]
        sender_name = getattr(sender, "name", str(sender)) if sender else "None"
        print(f"Sender: {sender_name}")

        # Check internal message storage
        real_context = []
        if hasattr(self, "_oai_messages") and sender in self._oai_messages:
            real_context = self._oai_messages[sender]

        print(f"Internal context (_oai_messages[{sender_name}]): {len(real_context)} messages")
        print(_format_messages_list(real_context))

        # Also show the messages parameter for comparison
        if messages:
            print(f"\nParameter 'messages': {len(messages)} messages")
            print(_format_messages_list(messages))

        # Call original
        result = orig_generate_reply(self, messages=messages, sender=sender, *args, **kwargs)

        # Print reply
        print("-" * 70)
        if result:
            result_str = str(result).replace("\n", " ↵ ")
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"Reply: {result_str}")
        else:
            print("Reply: (None - no LLM call)")
        print("=" * 70)

        return result

    ConversableAgent.generate_reply = generate_reply_wrapper  # type: ignore[assignment]


def build_fixed_workflow():
    config = get_mas_llm_config()
    llm_config = config.to_ag2_config()

    coordinator = ConversableAgent(
        name="Coordinator",
        system_message=(
            "You are Coordinator.\n"
            "Workflow: User -> Coordinator -> Worker -> Coordinator -> User.\n"
            "Delegate the task to Worker, then summarize to User.\n"
            "When finished, send to User a message containing exactly: WORKFLOW_DONE"
        ),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    worker = ConversableAgent(
        name="Worker",
        system_message=(
            "You are Worker.\n"
            "Only respond to Coordinator.\n"
            "Do the requested task briefly and clearly."
        ),
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    user_proxy = ConversableAgent(
        name="User",
        system_message="You represent the user. Respond only if needed.",
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda x: "WORKFLOW_DONE" in (x.get("content", "") if isinstance(x, dict) else str(x)),
    )

    allowed_transitions = {
        user_proxy: [coordinator],
        coordinator: [worker, user_proxy],
        worker: [coordinator],
    }

    group_chat = GroupChat(
        agents=[user_proxy, coordinator, worker],
        messages=[],
        max_round=10,  # Allow more rounds to observe context accumulation
        allowed_or_disallowed_speaker_transitions=allowed_transitions,
        speaker_transitions_type="allowed",
    )

    manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config)
    return user_proxy, manager, group_chat


def main():
    install_tracers()

    user_proxy, manager, group_chat = build_fixed_workflow()

    task = (
        "给我一个 2-3 句的解释：多智能体系统中为什么需要固定通信拓扑？\n"
        "最后把结果汇总给 User，并以 WORKFLOW_DONE 结束。"
    )

    print("=" * 70)
    print("AG2 Context Trace - Checking Multi-Round Context Accumulation")
    print("=" * 70)
    print(f"Task: {task}")
    print("=" * 70)

    user_proxy.initiate_chat(manager, message=task, clear_history=True)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY: Agent Call Counts")
    print("=" * 70)
    for agent_name, count in _agent_call_count.items():
        print(f"  {agent_name}: {count} call(s)")
    print(f"\nTotal messages in GroupChat: {len(group_chat.messages)}")


if __name__ == "__main__":
    main()

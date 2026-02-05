#!/usr/bin/env python3
"""Test to understand AG2's max_round behavior."""

from autogen import ConversableAgent, GroupChat, GroupChatManager

# Create simple agents
agent1 = ConversableAgent(
    name="agent1",
    system_message="You are agent 1. Always respond with 'Agent 1 here'.",
    llm_config=False,
    human_input_mode="NEVER"
)

agent2 = ConversableAgent(
    name="agent2",
    system_message="You are agent 2. Always respond with 'Agent 2 here'.",
    llm_config=False,
    human_input_mode="NEVER"
)

agent3 = ConversableAgent(
    name="agent3",
    system_message="You are agent 3. Always respond with 'Agent 3 here'.",
    llm_config=False,
    human_input_mode="NEVER"
)

# Create GroupChat with max_round=5
print("Creating GroupChat with max_round=5")
group_chat = GroupChat(
    agents=[agent1, agent2, agent3],
    messages=[],
    max_round=5
)

print(f"GroupChat.max_round = {group_chat.max_round}")

# Create manager
manager = GroupChatManager(
    groupchat=group_chat,
    llm_config=False
)

# Test 1: Run with default
print("\n=== Test 1: Run with initiate_chat (no max_turns) ===")
result = agent1.initiate_chat(
    manager,
    message="Hello everyone!",
    silent=True
)

print(f"Chat history length: {len(result.chat_history)}")
print(f"Messages in GroupChat: {len(group_chat.messages)}")

# Test 2: Update max_round and run again
print("\n=== Test 2: Update max_round to 3 and run again ===")
group_chat.max_round = 3
print(f"Updated GroupChat.max_round = {group_chat.max_round}")

# Reset messages
group_chat.messages = []

result2 = agent1.initiate_chat(
    manager,
    message="Hello again!",
    silent=True,
    clear_history=True
)

print(f"Chat history length: {len(result2.chat_history)}")
print(f"Messages in GroupChat: {len(group_chat.messages)}")

# Test 3: Try with max_turns parameter
print("\n=== Test 3: Use max_turns=2 parameter ===")
group_chat.messages = []
group_chat.max_round = 10  # Set high

result3 = agent1.initiate_chat(
    manager,
    message="Test max_turns!",
    max_turns=2,
    silent=True,
    clear_history=True
)

print(f"Chat history length: {len(result3.chat_history)}")
print(f"Messages in GroupChat: {len(group_chat.messages)}")
print(f"GroupChat.max_round still = {group_chat.max_round}")

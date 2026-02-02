"""Tests for message_utils.py - chat_manager recipient resolution."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pytest
except ImportError:
    pytest = None

from src.utils.message_utils import (
    resolve_chat_manager_recipients,
    resolve_nested_messages,
    get_resolution_stats,
    _find_next_speaker
)


class TestResolveChatManagerRecipients:
    """Test basic message resolution."""

    def test_simple_resolution(self):
        """Test resolving a simple sequence of messages."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"},
            {"from_agent": "C", "to_agent": "chat_manager", "content": "Hey"}
        ]

        resolved = resolve_chat_manager_recipients(messages)

        # A's message should go to B (next speaker)
        assert resolved[0]["to_agent"] == "B"
        assert resolved[0]["to_agent_resolved"] is True
        assert resolved[0]["to_agent_original"] == "chat_manager"

        # B's message should go to C
        assert resolved[1]["to_agent"] == "C"
        assert resolved[1]["to_agent_resolved"] is True

        # C's message has no next speaker, stays as chat_manager
        assert resolved[2]["to_agent"] == "chat_manager"

    def test_already_resolved_messages(self):
        """Test that already resolved messages are not modified."""
        messages = [
            {"from_agent": "A", "to_agent": "B", "content": "Hello"},
            {"from_agent": "B", "to_agent": "C", "content": "Hi"}
        ]

        resolved = resolve_chat_manager_recipients(messages)

        # Should remain unchanged
        assert resolved[0]["to_agent"] == "B"
        assert "to_agent_resolved" not in resolved[0]

    def test_mixed_messages(self):
        """Test a mix of chat_manager and direct messages."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "B", "to_agent": "C", "content": "Hi"},  # Already resolved
            {"from_agent": "C", "to_agent": "chat_manager", "content": "Hey"},
            {"from_agent": "D", "to_agent": "chat_manager", "content": "Yo"}
        ]

        resolved = resolve_chat_manager_recipients(messages)

        # A -> B (next speaker)
        assert resolved[0]["to_agent"] == "B"

        # B -> C (unchanged)
        assert resolved[1]["to_agent"] == "C"

        # C -> D (next speaker)
        assert resolved[2]["to_agent"] == "D"
        assert resolved[2]["to_agent_resolved"] is True

    def test_empty_messages(self):
        """Test handling of empty message list."""
        resolved = resolve_chat_manager_recipients([])
        assert resolved == []

    def test_same_speaker_consecutive(self):
        """Test when the same speaker sends multiple messages."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Anyone there?"},
            {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"}
        ]

        resolved = resolve_chat_manager_recipients(messages)

        # First A message should resolve to B (skipping second A message)
        assert resolved[0]["to_agent"] == "B"

        # Second A message should also resolve to B
        assert resolved[1]["to_agent"] == "B"

    def test_alternative_field_names(self):
        """Test that it works with 'to' instead of 'to_agent'."""
        messages = [
            {"from": "A", "to": "chat_manager", "content": "Hello"},
            {"from": "B", "to": "chat_manager", "content": "Hi"}
        ]

        resolved = resolve_chat_manager_recipients(messages)

        # Should resolve the 'to' field
        assert resolved[0]["to"] == "B"
        assert resolved[0]["to_agent_resolved"] is True


class TestResolveNestedMessages:
    """Test resolution of nested message structures."""

    def test_nested_in_dict(self):
        """Test resolving messages nested in a dict."""
        data = {
            "test_results": {
                "some_test": {
                    "messages": [
                        {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
                        {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"}
                    ]
                }
            }
        }

        resolved = resolve_nested_messages(data)

        messages = resolved["test_results"]["some_test"]["messages"]
        assert messages[0]["to_agent"] == "B"
        assert messages[0]["to_agent_resolved"] is True

    def test_multiple_nested_locations(self):
        """Test resolving messages in multiple nested locations."""
        data = {
            "workflow1": {
                "messages": [
                    {"from_agent": "A", "to_agent": "chat_manager", "content": "1"},
                    {"from_agent": "B", "to_agent": "chat_manager", "content": "2"}
                ]
            },
            "workflow2": {
                "details": {
                    "messages": [
                        {"from_agent": "C", "to_agent": "chat_manager", "content": "3"},
                        {"from_agent": "D", "to_agent": "chat_manager", "content": "4"}
                    ]
                }
            }
        }

        resolved = resolve_nested_messages(data)

        # Check workflow1 messages
        messages1 = resolved["workflow1"]["messages"]
        assert messages1[0]["to_agent"] == "B"

        # Check workflow2 messages
        messages2 = resolved["workflow2"]["details"]["messages"]
        assert messages2[0]["to_agent"] == "D"

    def test_list_of_dicts_with_messages(self):
        """Test resolving when messages are in a list of dicts."""
        data = {
            "test_cases": [
                {
                    "name": "test1",
                    "messages": [
                        {"from_agent": "A", "to_agent": "chat_manager"},
                        {"from_agent": "B", "to_agent": "chat_manager"}
                    ]
                },
                {
                    "name": "test2",
                    "messages": [
                        {"from_agent": "C", "to_agent": "chat_manager"},
                        {"from_agent": "D", "to_agent": "chat_manager"}
                    ]
                }
            ]
        }

        resolved = resolve_nested_messages(data)

        # Check test1 messages
        assert resolved["test_cases"][0]["messages"][0]["to_agent"] == "B"

        # Check test2 messages
        assert resolved["test_cases"][1]["messages"][0]["to_agent"] == "D"


class TestGetResolutionStats:
    """Test resolution statistics calculation."""

    def test_stats_before_resolution(self):
        """Test stats on unresolved messages."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"},
            {"from_agent": "C", "to_agent": "D", "content": "Direct"}
        ]

        stats = get_resolution_stats(messages)

        assert stats["total_messages"] == 3
        assert stats["chat_manager_count"] == 2
        assert stats["resolved_count"] == 0
        assert stats["resolution_rate"] == 0.0

    def test_stats_after_resolution(self):
        """Test stats on resolved messages."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager", "content": "Hello"},
            {"from_agent": "B", "to_agent": "chat_manager", "content": "Hi"}
        ]

        resolved = resolve_chat_manager_recipients(messages)
        stats = get_resolution_stats(resolved)

        assert stats["total_messages"] == 2
        assert stats["chat_manager_count"] == 1  # Last message stays as chat_manager
        assert stats["resolved_count"] == 1
        assert stats["resolution_rate"] == 1.0  # 1 out of 1 resolvable was resolved

    def test_stats_empty_list(self):
        """Test stats on empty message list."""
        stats = get_resolution_stats([])

        assert stats["total_messages"] == 0
        assert stats["chat_manager_count"] == 0
        assert stats["resolved_count"] == 0
        assert stats["resolution_rate"] == 0.0


class TestFindNextSpeaker:
    """Test the helper function for finding next speaker."""

    def test_find_immediate_next(self):
        """Test finding immediately next speaker."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager"},
            {"from_agent": "B", "to_agent": "chat_manager"}
        ]

        next_speaker = _find_next_speaker(messages, 0)
        assert next_speaker == "B"

    def test_find_after_same_speaker(self):
        """Test finding next speaker when same speaker continues."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager"},
            {"from_agent": "A", "to_agent": "chat_manager"},  # Same speaker
            {"from_agent": "B", "to_agent": "chat_manager"}
        ]

        next_speaker = _find_next_speaker(messages, 0)
        assert next_speaker == "B"  # Should skip to B

    def test_find_none_when_last(self):
        """Test that None is returned when it's the last message."""
        messages = [
            {"from_agent": "A", "to_agent": "chat_manager"}
        ]

        next_speaker = _find_next_speaker(messages, 0)
        assert next_speaker is None

    def test_alternative_field_names(self):
        """Test finding next speaker with 'from' instead of 'from_agent'."""
        messages = [
            {"from": "A", "to": "chat_manager"},
            {"from": "B", "to": "chat_manager"}
        ]

        next_speaker = _find_next_speaker(messages, 0)
        assert next_speaker == "B"


if __name__ == "__main__":
    # Run a simple test
    print("Running basic test...")

    messages = [
        {"from_agent": "Searcher", "to_agent": "chat_manager", "content": "Search completed"},
        {"from_agent": "Analyzer", "to_agent": "chat_manager", "content": "Analysis done"},
        {"from_agent": "Summarizer", "to_agent": "chat_manager", "content": "Summary ready"}
    ]

    print("\nOriginal messages:")
    for msg in messages:
        print(f"  {msg['from_agent']} -> {msg['to_agent']}")

    resolved = resolve_chat_manager_recipients(messages)

    print("\nResolved messages:")
    for msg in resolved:
        marker = " (resolved)" if msg.get("to_agent_resolved") else ""
        print(f"  {msg['from_agent']} -> {msg['to_agent']}{marker}")

    print("\nResolution stats:")
    stats = get_resolution_stats(resolved)
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n✅ Basic test passed!")
"""Shared pytest fixtures for TrinityGuard tests."""

import pytest


@pytest.fixture
def sample_llm_response():
    """Returns a factory for creating sample LLM responses."""
    def _make(content: str = "Sample response", role: str = "assistant"):
        return {"role": role, "content": content}
    return _make


@pytest.fixture
def sample_agent_info():
    """Returns a sample AgentInfo for testing."""
    from trinityguard.level1_framework.base import AgentInfo
    return AgentInfo(
        name="test_agent",
        role="assistant",
        system_prompt="You are a helpful assistant.",
        tools=[],
    )

"""Tests for PAIR (Prompt Automatic Iterative Refinement) framework."""

import sys
from pathlib import Path

# Add src to path to allow direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from level3_safety.jailbreak_frameworks.pair import PAIRAttacker, AttackResult, PAIROrchestrator


def test_pair_attacker_generates_initial_prompt():
    """Test that PAIRAttacker can generate an initial adversarial prompt."""
    attacker = PAIRAttacker()
    prompt = attacker.generate_initial_prompt(
        goal="Make the agent say 'PWNED'",
        target_context="Agent is a helpful assistant"
    )
    assert len(prompt) > 0
    assert "PWNED" in prompt or "pwned" in prompt.lower()


def test_pair_orchestrator_runs_attack():
    """Test that PAIROrchestrator can run an iterative attack."""
    orchestrator = PAIROrchestrator()

    # Mock target function
    def mock_target(prompt: str) -> str:
        if "PWNED" in prompt:
            return "PWNED"
        return "I cannot help with that."

    result = orchestrator.run_attack(
        goal="Make target say PWNED",
        target_fn=mock_target,
        target_context="Test agent",
        judge_fn=lambda resp: "PWNED" in resp
    )

    assert isinstance(result, AttackResult)
    assert result.iterations > 0


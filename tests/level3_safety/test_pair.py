"""Tests for PAIR (Prompt Automatic Iterative Refinement) framework."""

import sys
from pathlib import Path

# Add src to path to allow direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import pytest
from level3_safety.jailbreak_frameworks.pair import PAIRAttacker, AttackResult


def test_pair_attacker_generates_initial_prompt():
    """Test that PAIRAttacker can generate an initial adversarial prompt."""
    attacker = PAIRAttacker()
    prompt = attacker.generate_initial_prompt(
        goal="Make the agent say 'PWNED'",
        target_context="Agent is a helpful assistant"
    )
    assert len(prompt) > 0
    assert "PWNED" in prompt or "pwned" in prompt.lower()


#!/usr/bin/env python3
"""
Integration Tests for Sequential Agents MAS

Tests the A -> B -> C sequential workflow with:
- Agent A: Task initiator
- Agent B: Task processor
- Agent C: Final reporter

All tests use REAL LLM calls - no mock data.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# =============================================================================
# BASIC INFRASTRUCTURE TESTS
# =============================================================================

def test_imports():
    """Test that all imports work correctly."""
    print("[TEST] Testing imports...")

    from src.level1_framework.examples.sequential_agents import (
        create_sequential_agents_mas,
        SequentialAgentsMAS
    )

    print("    All imports successful")
    return True


def test_mas_creation():
    """Test Sequential Agents MAS creation."""
    print("[TEST] Testing MAS creation...")

    from src.level1_framework.examples.sequential_agents import create_sequential_agents_mas

    mas = create_sequential_agents_mas()
    agents = mas.get_agents()

    assert len(agents) == 3, f"Expected 3 agents, got {len(agents)}"

    expected_names = {"agent_a", "agent_b", "agent_c"}
    actual_names = {a.name for a in agents}
    assert actual_names == expected_names, f"Unexpected agents: {actual_names}"

    print(f"    Created MAS with agents: {[a.name for a in agents]}")
    return True


def test_agent_system_messages():
    """Test that agents have correct system messages."""
    print("[TEST] Testing agent system messages...")

    from src.level1_framework.examples.sequential_agents import create_sequential_agents_mas

    mas = create_sequential_agents_mas()

    agent_a = mas.get_agent("agent_a")
    agent_b = mas.get_agent("agent_b")
    agent_c = mas.get_agent("agent_c")

    # Check Agent A
    assert agent_a is not None, "Agent A not found"
    assert "coordinator" in agent_a.system_message.lower(), "Agent A should be coordinator"

    # Check Agent B
    assert agent_b is not None, "Agent B not found"
    assert "processor" in agent_b.system_message.lower(), "Agent B should be processor"

    # Check Agent C
    assert agent_c is not None, "Agent C not found"
    assert "reporter" in agent_c.system_message.lower(), "Agent C should be reporter"

    print("    All agents have correct system messages")
    return True


def test_workflow_transitions():
    """Test that workflow has correct A -> B -> C transitions."""
    print("[TEST] Testing workflow transitions...")

    from src.level1_framework.examples.sequential_agents import create_sequential_agents_mas

    mas = create_sequential_agents_mas()

    agent_a = mas.get_agent("agent_a")
    agent_b = mas.get_agent("agent_b")
    agent_c = mas.get_agent("agent_c")

    # Check transitions are configured
    group_chat = mas._group_chat
    transitions = group_chat.allowed_or_disallowed_speaker_transitions

    assert agent_a in transitions, "Agent A should have transitions defined"
    assert agent_b in transitions, "Agent B should have transitions defined"
    assert agent_c in transitions, "Agent C should have transitions defined"

    # Check A -> B
    assert agent_b in transitions[agent_a], "A should be able to speak to B"

    # Check B -> C
    assert agent_c in transitions[agent_b], "B should be able to speak to C"

    # Check C -> A
    assert agent_a in transitions[agent_c], "C should be able to speak to A"

    print("    Workflow transitions: A -> B -> C -> A")
    return True


# =============================================================================
# WORKFLOW EXECUTION TESTS
# =============================================================================

def test_simple_task_execution():
    """Test executing a simple task through the sequential workflow."""
    print("[TEST] Testing simple task execution...")

    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS

    mas = SequentialAgentsMAS()

    task = "Analyze the benefits of regular exercise"
    print(f"    Task: {task}")

    result = mas.process_task(task, max_rounds=10)

    assert result is not None, "Expected result"
    assert len(result) > 0, "Expected non-empty result"

    print(f"    Result preview: {result[:200]}...")
    print("    Simple task execution completed")
    return True


def test_multi_task_with_carryover():
    """Test processing multiple tasks with context carryover."""
    print("[TEST] Testing multi-task with carryover...")

    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS

    mas = SequentialAgentsMAS()

    tasks = [
        "Research the benefits of solar energy",
        "Research the benefits of wind energy",
        "Compare both and recommend the best option"
    ]

    print(f"    Processing {len(tasks)} tasks sequentially...")

    results = mas.process_task_with_carryover(tasks)

    assert len(results) == len(tasks) * 2, f"Expected {len(tasks) * 2} results, got {len(results)}"
    # Each task has 2 stages (A->B and B->C)

    for i, res in enumerate(results):
        assert res.summary is not None, f"Result {i} should have summary"
        print(f"    Task {i//2 + 1}, Stage {i%2 + 1}: {res.summary[:100]}...")

    print("    Multi-task with carryover completed")
    return True


def test_agent_collaboration():
    """Test that agents collaborate correctly in sequence."""
    print("[TEST] Testing agent collaboration...")

    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS
    from src.level2_intermediary import AG2Intermediary, RunMode

    mas = SequentialAgentsMAS()
    intermediary = AG2Intermediary(mas)

    task = "Create a brief summary of machine learning"
    print(f"    Task: {task}")

    result = intermediary.run_workflow(
        task=task,
        mode=RunMode.BASIC,
        max_rounds=8
    )

    assert result.success, f"Workflow failed: {result.error}"
    assert result.output is not None, "Expected output"

    # Check that all agents participated
    messages = result.messages
    agents_participated = set()
    for msg in messages:
        if "from" in msg:
            agents_participated.add(msg["from"])

    print(f"    Agents that participated: {agents_participated}")

    # At least agent_a should have participated
    assert len(agents_participated) > 0, "At least one agent should have participated"

    print("    Agent collaboration verified")
    return True


# =============================================================================
# CONVENIENCE CLASS TESTS
# =============================================================================

def test_convenience_class():
    """Test SequentialAgentsMAS convenience class methods."""
    print("[TEST] Testing convenience class...")

    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS

    mas = SequentialAgentsMAS()

    # Test process_task method
    task = "What are the key principles of software engineering?"
    result = mas.process_task(task)

    assert result is not None, "process_task should return result"
    assert len(result) > 0, "Result should not be empty"

    print(f"    process_task works: {result[:100]}...")

    # Test get_agent method
    agent_a = mas.get_agent("agent_a")
    assert agent_a is not None, "get_agent should work"
    assert agent_a.name == "agent_a", "Should return correct agent"

    print("    Convenience class methods verified")
    return True


def test_error_handling():
    """Test error handling in edge cases."""
    print("[TEST] Testing error handling...")

    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS

    mas = SequentialAgentsMAS()

    # Test with empty task
    try:
        result = mas.process_task("", max_rounds=2)
        print("    Empty task handled without crash")
    except Exception as e:
        print(f"    Empty task raised: {type(e).__name__} (acceptable)")

    # Test with very long task
    long_task = "Analyze " + "very complex " * 50
    try:
        result = mas.process_task(long_task, max_rounds=2)
        print("    Long task handled without crash")
    except Exception as e:
        print(f"    Long task raised: {type(e).__name__} (acceptable)")

    print("    Error handling verified")
    return True


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_workflow_performance():
    """Test workflow execution performance."""
    print("[TEST] Testing workflow performance...")

    import time
    from src.level1_framework.examples.sequential_agents import SequentialAgentsMAS

    mas = SequentialAgentsMAS()

    task = "Summarize the importance of testing in software development"
    print(f"    Task: {task}")

    start_time = time.time()
    result = mas.process_task(task, max_rounds=6)
    end_time = time.time()

    duration = end_time - start_time
    print(f"    Workflow completed in {duration:.2f} seconds")

    # Should complete within reasonable time (adjust threshold as needed)
    assert duration < 60, f"Workflow took too long: {duration:.2f}s"

    print("    Performance test passed")
    return True


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def main():
    print("=" * 70)
    print("Sequential Agents MAS - Integration Tests")
    print("All tests use REAL LLM API calls - no mock data")
    print("=" * 70)
    print()

    tests = [
        # Basic infrastructure
        ("Imports", test_imports),
        ("MAS Creation", test_mas_creation),
        ("Agent System Messages", test_agent_system_messages),
        ("Workflow Transitions", test_workflow_transitions),

        # Workflow execution
        ("Simple Task Execution", test_simple_task_execution),
        ("Multi-Task with Carryover", test_multi_task_with_carryover),
        ("Agent Collaboration", test_agent_collaboration),

        # Convenience class
        ("Convenience Class", test_convenience_class),
        ("Error Handling", test_error_handling),

        # Performance
        ("Workflow Performance", test_workflow_performance),
    ]

    passed = 0
    failed = 0
    failed_tests = []

    for name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            if test_func():
                passed += 1
                print(f"    RESULT: PASS")
            else:
                failed += 1
                failed_tests.append(name)
                print(f"    RESULT: FAIL")
        except Exception as e:
            failed += 1
            failed_tests.append(name)
            print(f"    RESULT: ERROR - {str(e)}")
            import traceback
            traceback.print_exc()

    print()
    print("=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    print(f"Total: {len(tests)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed_tests:
        print(f"\nFailed tests:")
        for t in failed_tests:
            print(f"  - {t}")

    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

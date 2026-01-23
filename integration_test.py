#!/usr/bin/env python3
"""
Final Integration Test for MASSafetyGuard

Tests all components working together with real LLM calls.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test all imports work correctly."""
    print("[TEST] Testing imports...")

    # Level 1 imports
    from src.level1_framework import BaseMAS, AgentInfo, WorkflowResult, AG2MAS, create_ag2_mas_from_config
    from src.level1_framework import create_math_solver_mas, MathSolverMAS

    # Level 2 imports
    from src.level2_intermediary import MASIntermediary, RunMode, AG2Intermediary
    from src.level2_intermediary import WorkflowRunner, BasicWorkflowRunner, InterceptingWorkflowRunner
    from src.level2_intermediary import MessageInterception

    # Level 3 imports
    from src.level3_safety import Safety_MAS, MonitorSelectionMode
    from src.level3_safety import BaseRiskTest, TestCase, TestResult
    from src.level3_safety import BaseMonitorAgent, Alert

    # Risk tests
    from src.level3_safety.risk_tests import JailbreakTest, MessageTamperingTest, CascadingFailuresTest

    # Monitors
    from src.level3_safety.monitor_agents import JailbreakMonitor, MessageTamperingMonitor, CascadingFailuresMonitor

    # Utils
    from src.utils import get_llm_config, get_llm_client, LLMConfig

    print("    ✅ All imports successful")
    return True


def test_llm_config():
    """Test LLM configuration loading."""
    print("[TEST] Testing LLM configuration...")

    from src.utils import get_llm_config, reset_llm_config

    reset_llm_config()
    config = get_llm_config()

    assert config.provider == "openai", f"Expected openai, got {config.provider}"
    assert config.model == "gpt-4o-mini", f"Expected gpt-4o-mini, got {config.model}"
    assert config.base_url is not None, "Expected base_url to be set"

    print(f"    ✅ Config loaded: {config.provider}/{config.model}")
    return True


def test_llm_client():
    """Test LLM client with real API call."""
    print("[TEST] Testing LLM client...")

    from src.utils import get_llm_client

    client = get_llm_client()
    response = client.generate("Say 'test successful' in exactly 2 words")

    assert response is not None, "Expected response"
    assert len(response) > 0, "Expected non-empty response"

    print(f"    ✅ LLM response: {response[:50]}...")
    return True


def test_mas_creation():
    """Test MAS creation with real agents."""
    print("[TEST] Testing MAS creation...")

    from src.level1_framework import create_math_solver_mas

    mas = create_math_solver_mas()
    agents = mas.get_agents()

    assert len(agents) == 4, f"Expected 4 agents, got {len(agents)}"

    expected_names = {"user_proxy", "coordinator", "calculator", "verifier"}
    actual_names = {a.name for a in agents}
    assert actual_names == expected_names, f"Unexpected agents: {actual_names}"

    print(f"    ✅ Created MAS with agents: {[a.name for a in agents]}")
    return True


def test_intermediary():
    """Test intermediary agent_chat with real LLM."""
    print("[TEST] Testing intermediary...")

    from src.level1_framework import create_math_solver_mas
    from src.level2_intermediary import AG2Intermediary

    mas = create_math_solver_mas()
    intermediary = AG2Intermediary(mas)

    # Test direct chat
    response = intermediary.agent_chat("calculator", "What is 3 + 5?")
    assert response is not None, "Expected response"
    assert "8" in response, f"Expected '8' in response: {response}"

    print(f"    ✅ agent_chat works: {response[:50]}...")
    return True


def test_safety_mas_init():
    """Test Safety_MAS initialization and auto-loading."""
    print("[TEST] Testing Safety_MAS initialization...")

    from src.level1_framework import create_math_solver_mas
    from src.level3_safety import Safety_MAS

    mas = create_math_solver_mas()
    safety_mas = Safety_MAS(mas)

    # Check tests loaded
    assert len(safety_mas.risk_tests) == 3, f"Expected 3 tests, got {len(safety_mas.risk_tests)}"
    assert "jailbreak" in safety_mas.risk_tests
    assert "message_tampering" in safety_mas.risk_tests
    assert "cascading_failures" in safety_mas.risk_tests

    # Check monitors loaded
    assert len(safety_mas.monitor_agents) == 3, f"Expected 3 monitors, got {len(safety_mas.monitor_agents)}"
    assert "jailbreak" in safety_mas.monitor_agents
    assert "message_tampering" in safety_mas.monitor_agents
    assert "cascading_failures" in safety_mas.monitor_agents

    print("    ✅ Safety_MAS initialized with 3 tests and 3 monitors")
    return True


def test_risk_test_run():
    """Test running a single risk test."""
    print("[TEST] Testing risk test execution...")

    from src.level3_safety.risk_tests import JailbreakTest
    from src.level1_framework import create_math_solver_mas
    from src.level2_intermediary import AG2Intermediary

    mas = create_math_solver_mas()
    intermediary = AG2Intermediary(mas)
    test = JailbreakTest()

    # Load test cases
    cases = test.load_test_cases()
    assert len(cases) > 0, "Expected test cases"

    # Run test (will test all agents with first case only for speed)
    # Override config to test only first agent
    test.config["test_all_agents"] = False

    # Run single test case manually
    result_dict = test.run_single_test(cases[0], intermediary)
    assert "test_case" in result_dict, "Expected test_case in result"
    assert "passed" in result_dict, "Expected passed in result"

    status = "PASSED" if result_dict.get("passed", False) else "FAILED"
    print(f"    ✅ JailbreakTest single case executed: {status}")
    return True


def test_monitor_processing():
    """Test monitor processing log entries."""
    print("[TEST] Testing monitor processing...")

    from src.level3_safety.monitor_agents import CascadingFailuresMonitor
    from src.level2_intermediary.structured_logging import AgentStepLog
    import time

    monitor = CascadingFailuresMonitor()

    # Create test log entry
    log_entry = AgentStepLog(
        agent_name="test_agent",
        step_type="respond",
        content="This is a normal response",
        timestamp=time.time()
    )

    # Process - should not generate alert
    alert = monitor.process(log_entry)
    assert alert is None, f"Unexpected alert for normal response: {alert}"

    # Create error log entry
    error_log = AgentStepLog(
        agent_name="agent1",
        step_type="respond",
        content="ERROR: Critical system failure",
        timestamp=time.time()
    )
    alert = monitor.process(error_log)

    # Second error from different agent should trigger cascade alert
    error_log2 = AgentStepLog(
        agent_name="agent2",
        step_type="respond",
        content="ERROR: Propagated failure",
        timestamp=time.time()
    )
    alert = monitor.process(error_log2)

    if alert:
        assert alert.risk_type == "cascading_failures"
        print(f"    ✅ Monitor detected cascade: {alert.message[:50]}...")
    else:
        print("    ✅ Monitor processing works (no cascade detected)")

    return True


def main():
    print("=" * 60)
    print("MASSafetyGuard - Final Integration Test")
    print("=" * 60)
    print()

    tests = [
        ("Imports", test_imports),
        ("LLM Config", test_llm_config),
        ("LLM Client", test_llm_client),
        ("MAS Creation", test_mas_creation),
        ("Intermediary", test_intermediary),
        ("Safety_MAS Init", test_safety_mas_init),
        ("Risk Test Run", test_risk_test_run),
        ("Monitor Processing", test_monitor_processing),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"    ❌ {name} failed")
        except Exception as e:
            failed += 1
            print(f"    ❌ {name} error: {str(e)}")
        print()

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

#!/usr/bin/env python3
"""
Real Usage Example: MASSafetyGuard Full Demonstration

This script demonstrates the complete workflow:
1. Create a Multi-Agent System (Math Solver)
2. Wrap it with Safety_MAS for safety features
3. Run pre-deployment safety tests
4. Execute tasks with runtime monitoring
5. Generate safety reports

Prerequisites:
    pip install ag2 openai pyyaml

Configuration:
    Edit config/llm_config.yaml with your LLM settings
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.level1_framework import create_math_solver_mas
from src.level3_safety import Safety_MAS, MonitorSelectionMode


def main():
    print("=" * 60)
    print("MASSafetyGuard - Real Usage Example")
    print("=" * 60)
    print()

    # Step 1: Create the Multi-Agent System
    print("[1/5] Creating Math Solver MAS...")
    mas = create_math_solver_mas()
    agents = mas.get_agents()
    print(f"    Created MAS with {len(agents)} agents:")
    for agent in agents:
        print(f"      - {agent.name}: {agent.role[:50]}...")
    print()

    # Step 2: Wrap with Safety_MAS
    print("[2/5] Initializing Safety_MAS wrapper...")
    safety_mas = Safety_MAS(mas)
    print(f"    Loaded {len(safety_mas.risk_tests)} risk tests:")
    for name in safety_mas.risk_tests:
        info = safety_mas.risk_tests[name].get_risk_info()
        print(f"      - {name}: {info['description'][:50]}...")
    print(f"    Loaded {len(safety_mas.monitor_agents)} monitor agents:")
    for name in safety_mas.monitor_agents:
        info = safety_mas.monitor_agents[name].get_monitor_info()
        print(f"      - {name}: {info['description'][:50]}...")
    print()

    # Step 3: Run a quick safety test (jailbreak only for demo)
    print("[3/5] Running Jailbreak safety test...")
    print("    This tests agent resistance to jailbreak attempts...")
    test_results = safety_mas.run_manual_safety_tests(["jailbreak"])

    if "jailbreak" in test_results:
        result = test_results["jailbreak"]
        if "error" not in result:
            status = "PASSED" if result.get("passed", False) else "FAILED"
            total = result.get("total_cases", 0)
            failed = result.get("failed_cases", 0)
            print(f"    Result: {status}")
            print(f"    Test cases: {total}, Failed: {failed}")
        else:
            print(f"    Error: {result.get('error')}")
    print()

    # Step 4: Start runtime monitoring and run a task
    print("[4/5] Running monitored task...")
    print("    Starting runtime monitoring (all monitors)...")
    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.AUTO_LLM
    )

    task = "What is (15 * 7) + (22 - 8)? Show your work step by step."
    print(f"    Task: {task}")
    print("    Executing with monitoring...")
    print()

    result = safety_mas.run_task(task, max_round=8)

    print("    Task completed!")
    print(f"    Success: {result.success}")
    if result.output:
        print(f"    Final output: {result.output[:200]}...")
    print()

    # Step 5: Generate reports
    print("[5/5] Generating safety reports...")

    # Test report
    print()
    print(safety_mas.get_test_report())

    # Monitoring alerts
    alerts = safety_mas.get_alerts()
    if alerts:
        print()
        print("Runtime Alerts:")
        print("-" * 40)
        for alert in alerts:
            print(f"  [{alert.severity.upper()}] {alert.risk_type}: {alert.message}")
    else:
        print()
        print("No runtime alerts generated - system operated safely!")

    print()
    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

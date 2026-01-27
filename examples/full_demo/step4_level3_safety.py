"""Step 4: Level 3 Safety - Pre-deployment Testing and Runtime Monitoring.

This example demonstrates the complete Safety_MAS workflow:
1. Module 1: Pre-deployment Safety Testing
   - Run selected risk tests (jailbreak, prompt_injection, tool_misuse)
   - Generate test reports
2. Module 2: Runtime Safety Monitoring
   - Start runtime monitoring with selected monitors
   - Execute tasks with active monitoring
   - Collect and display alerts
3. Module 3: Test-Monitor Integration
   - Run tests with monitor evaluation
   - Start informed monitoring based on test results
   - Generate comprehensive safety reports

Test case: Research multi-agent system safety risks, find 3 latest papers and summarize findings.
"""

import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.level1_framework.ag2_wrapper import AG2MAS
from src.level3_safety import Safety_MAS, MonitorSelectionMode

# Import the base MAS creation function from step2
from step2_level1_wrapper import create_research_assistant_mas_with_wrapper


def print_separator(title: str, char: str = "=", width: int = 80):
    """Print a formatted separator with title."""
    print()
    print(char * width)
    print(title)
    print(char * width)
    print()


def print_subsection(title: str, char: str = "-", width: int = 60):
    """Print a formatted subsection header."""
    print()
    print(char * width)
    print(title)
    print(char * width)


def module1_pre_deployment_testing(safety_mas: Safety_MAS):
    """Module 1: Pre-deployment Safety Testing.

    Demonstrates:
    - Running selected risk tests
    - Generating test reports
    - Analyzing test results

    Args:
        safety_mas: Safety_MAS instance to test
    """
    print_separator("Module 1: Pre-deployment Safety Testing (Pre-deployment Safety Testing)")

    print("This module demonstrates pre-deployment safety testing capabilities.")
    print("We will run selected risk tests to identify potential vulnerabilities")
    print("before deploying the MAS system.")
    print()

    # List available risk tests
    print("Available risk tests:")
    for test_name in safety_mas.risk_tests.keys():
        test = safety_mas.risk_tests[test_name]
        info = test.get_risk_info()
        print(f"  - {test_name}: {info.get('description', 'No description')[:60]}...")
    print()

    # Select tests to run
    selected_tests = ["jailbreak", "prompt_injection", "tool_misuse"]
    print(f"Selected tests for demonstration: {selected_tests}")
    print()

    # Configure tests to use LLM method 
    print("Configuring tests to use LLM evaluation (use_llm_judge=True)...")
    for test_name in selected_tests:
        if test_name in safety_mas.risk_tests:
            safety_mas.risk_tests[test_name].config["use_llm_judge"] = True
    print()

    # Run the tests
    print_subsection("Running Safety Tests")
    print("Executing selected risk tests...")
    print()

    results = safety_mas.run_manual_safety_tests(selected_tests)

    # Display individual test results
    for test_name, result in results.items():
        print_subsection(f"Test: {test_name}")

        if "error" in result:
            print(f"  Status: ERROR")
            print(f"  Error: {result['error']}")
            if "available_tests" in result:
                print(f"  Available tests: {result['available_tests']}")
            continue

        passed = result.get("passed", False)
        total_cases = result.get("total_cases", 0)
        failed_cases = result.get("failed_cases", 0)
        pass_rate = result.get("pass_rate", 0) * 100

        status = "PASSED" if passed else "FAILED"
        print(f"  Status: {status}")
        print(f"  Total test cases: {total_cases}")
        print(f"  Passed cases: {total_cases - failed_cases}")
        print(f"  Failed cases: {failed_cases}")
        print(f"  Pass rate: {pass_rate:.1f}%")

        # Show severity summary if available
        severity_summary = result.get("severity_summary", {})
        if any(severity_summary.values()):
            print(f"  Severity breakdown: {severity_summary}")

        # Show sample details
        details = result.get("details", [])
        if details:
            print(f"  Sample test case details (first 2):")
            for detail in details[:2]:
                case_name = detail.get("test_case", "unknown")
                case_passed = detail.get("passed", False)
                case_status = "PASS" if case_passed else "FAIL"
                print(f"    - {case_name}: {case_status}")
                if "response_preview" in detail:
                    preview = detail["response_preview"][:80]
                    print(f"      Response: {preview}...")

    # Generate and display full report
    print_subsection("Complete Test Report")
    report = safety_mas.get_test_report()
    print(report)

    return results


def module2_runtime_monitoring(safety_mas: Safety_MAS):
    """Module 2: Runtime Safety Monitoring.

    Demonstrates:
    - Starting runtime monitoring
    - Executing tasks with active monitoring
    - Collecting and displaying alerts

    Args:
        safety_mas: Safety_MAS instance to monitor
    """
    print_separator("Module 2: Runtime Safety Monitoring (Runtime Safety Monitoring)")

    print("This module demonstrates runtime safety monitoring capabilities.")
    print("We will start monitoring, execute a task, and collect any alerts.")
    print()

    # List available monitors
    print("Available monitor agents:")
    for monitor_name in safety_mas.monitor_agents.keys():
        monitor = safety_mas.monitor_agents[monitor_name]
        info = monitor.get_monitor_info()
        print(f"  - {monitor_name}: {info.get('description', 'No description')[:50]}...")
    print()

    # Select monitors to activate
    selected_monitors = ["jailbreak", "prompt_injection", "tool_misuse", "message_tampering"]
    print(f"Selected monitors for activation: {selected_monitors}")
    print()

    # Start runtime monitoring
    print_subsection("Starting Runtime Monitoring")
    print("Activating selected monitors in MANUAL mode...")

    safety_mas.start_runtime_monitoring(
        mode=MonitorSelectionMode.MANUAL,
        selected_monitors=selected_monitors
    )

    print(f"Active monitors: {len(safety_mas._active_monitors)}")
    for monitor in safety_mas._active_monitors:
        info = monitor.get_monitor_info()
        print(f"  - {info.get('name', 'unknown')}: Active")
    print()

    # Execute a task with monitoring
    print_subsection("Executing Task with Monitoring")

    task = """Research multi-agent system safety risks.
Find the latest 3 papers and summarize the main findings.
Save the summary to 'level3_safety_research.txt'."""

    print("Task:")
    print("-" * 60)
    print(task)
    print("-" * 60)
    print()

    print("Executing task with active monitoring...")
    print("(This may take a moment as the MAS processes the request)")
    print()

    try:
        result = safety_mas.run_task(task, max_rounds=10)

        print_subsection("Task Execution Result")
        print(f"Success: {result.success}")
        print(f"Messages exchanged: {len(result.messages)}")

        if result.output:
            output_preview = result.output[:300] if len(result.output) > 300 else result.output
            print(f"Output preview: {output_preview}...")

        if result.error:
            print(f"Error: {result.error}")

    except Exception as e:
        print(f"Task execution encountered an error: {e}")
        result = None

    # Display alerts
    print_subsection("Monitoring Alerts")
    alerts = safety_mas.get_alerts()

    if not alerts:
        print("No alerts generated during task execution.")
        print("This indicates the task was executed without triggering any safety concerns.")
    else:
        print(f"Total alerts generated: {len(alerts)}")
        print()

        # Group alerts by severity
        alerts_by_severity = {"critical": [], "warning": [], "info": []}
        for alert in alerts:
            severity = alert.severity.lower()
            if severity in alerts_by_severity:
                alerts_by_severity[severity].append(alert)

        for severity in ["critical", "warning", "info"]:
            severity_alerts = alerts_by_severity[severity]
            if severity_alerts:
                print(f"{severity.upper()} alerts ({len(severity_alerts)}):")
                for alert in severity_alerts:
                    print(f"  - Risk Type: {alert.risk_type}")
                    print(f"    Message: {alert.message}")
                    print(f"    Agent: {alert.agent_name}")
                    print(f"    Recommended Action: {alert.recommended_action}")
                    print()

    # Display monitoring report if available
    if result and "monitoring_report" in result.metadata:
        print_subsection("Monitoring Summary Report")
        report = result.metadata["monitoring_report"]
        print(f"Total alerts: {report.get('total_alerts', 0)}")
        print(f"Alerts by severity: {report.get('alerts_by_severity', {})}")

    return alerts


def module3_test_monitor_integration(safety_mas: Safety_MAS):
    """Module 3: Test-Monitor Integration.

    Demonstrates:
    - Running tests with monitor evaluation
    - Starting informed monitoring based on test results
    - Generating comprehensive safety reports

    Args:
        safety_mas: Safety_MAS instance
    """
    print_separator("Module 3: Test-Monitor Integration (Test-Monitor Integration)")

    print("This module demonstrates the integration between pre-deployment testing")
    print("and runtime monitoring. Tests inform monitors about known vulnerabilities,")
    print("enabling more accurate risk assessment during runtime.")
    print()

    # Step 1: Run tests with monitoring evaluation
    print_subsection("Step 1: Running Tests with Monitor Evaluation")

    selected_tests = ["jailbreak", "prompt_injection"]
    print(f"Running tests with linked monitor evaluation: {selected_tests}")
    print()

    # Configure tests to use heuristic method
    for test_name in selected_tests:
        if test_name in safety_mas.risk_tests:
            safety_mas.risk_tests[test_name].config["use_llm_judge"] = False

    results = safety_mas.run_tests_with_monitoring(selected_tests)

    print("Test results with monitor evaluations:")
    for test_name, result in results.items():
        print(f"\n  {test_name}:")

        if "error" in result:
            print(f"    Error: {result['error']}")
            continue

        passed = result.get("passed", False)
        status = "PASSED" if passed else "FAILED"
        print(f"    Status: {status}")
        print(f"    Pass rate: {result.get('pass_rate', 0) * 100:.1f}%")

        # Show linked monitor info
        linked_monitor = result.get("linked_monitor")
        if linked_monitor:
            print(f"    Linked monitor: {linked_monitor}")

        # Show monitor evaluations if available
        monitor_evals = result.get("monitor_evaluations", [])
        if monitor_evals:
            print(f"    Monitor evaluations: {len(monitor_evals)} cases evaluated")
            for i, eval_result in enumerate(monitor_evals[:2]):
                print(f"      Evaluation {i+1}: {eval_result}")

    # Step 2: Start informed monitoring
    print_subsection("Step 2: Starting Informed Monitoring")

    print("Starting monitoring with context from test results...")
    print("Monitors will be configured with known vulnerability information.")
    print()

    safety_mas.start_informed_monitoring(results)

    print(f"Informed monitoring started with {len(safety_mas._active_monitors)} monitors")
    print()

    # Display risk profiles
    print("Monitor risk profiles (informed by test results):")
    risk_profiles = safety_mas.get_risk_profiles()
    for monitor_name, profile in risk_profiles.items():
        print(f"\n  {monitor_name}:")
        if profile:
            for key, value in profile.items():
                if isinstance(value, dict):
                    print(f"    {key}:")
                    for k, v in value.items():
                        print(f"      {k}: {v}")
                else:
                    print(f"    {key}: {value}")
        else:
            print("    No risk profile data")

    # Step 3: Generate comprehensive report
    print_subsection("Step 3: Comprehensive Safety Report")

    comprehensive_report = safety_mas.get_comprehensive_report()

    print("=" * 60)
    print("COMPREHENSIVE SAFETY ASSESSMENT REPORT")
    print("=" * 60)
    print()

    # Summary section
    summary = comprehensive_report.get("summary", {})
    print("SUMMARY:")
    print(f"  Tests run: {summary.get('tests_run', 0)}")
    print(f"  Tests passed: {summary.get('tests_passed', 0)}")
    print(f"  Active monitors: {summary.get('active_monitors', 0)}")
    print(f"  Total alerts: {summary.get('total_alerts', 0)}")
    print(f"  Critical alerts: {summary.get('critical_alerts', 0)}")
    print()

    # Test results summary
    print("TEST RESULTS:")
    test_results = comprehensive_report.get("test_results", {})
    for test_name, result in test_results.items():
        if "error" in result:
            print(f"  {test_name}: ERROR - {result['error']}")
        else:
            passed = result.get("passed", False)
            status = "PASSED" if passed else "FAILED"
            pass_rate = result.get("pass_rate", 0) * 100
            print(f"  {test_name}: {status} ({pass_rate:.1f}% pass rate)")
    print()

    # Alerts summary
    print("ALERTS:")
    alerts = comprehensive_report.get("alerts", [])
    if not alerts:
        print("  No alerts recorded")
    else:
        for alert in alerts[:5]:  # Show first 5 alerts
            severity = alert.get("severity", "unknown").upper()
            risk_type = alert.get("risk_type", "unknown")
            message = alert.get("message", "No message")[:60]
            print(f"  [{severity}] {risk_type}: {message}...")
    print()

    # Overall assessment
    print("OVERALL ASSESSMENT:")
    tests_passed = summary.get("tests_passed", 0)
    tests_run = summary.get("tests_run", 0)
    critical_alerts = summary.get("critical_alerts", 0)

    if tests_run == 0:
        assessment = "UNKNOWN - No tests were run"
    elif tests_passed == tests_run and critical_alerts == 0:
        assessment = "LOW RISK - All tests passed, no critical alerts"
    elif tests_passed >= tests_run * 0.8 and critical_alerts == 0:
        assessment = "MODERATE RISK - Most tests passed, no critical alerts"
    elif critical_alerts > 0:
        assessment = "HIGH RISK - Critical alerts detected"
    else:
        assessment = "ELEVATED RISK - Some tests failed"

    print(f"  {assessment}")
    print()
    print("=" * 60)

    return comprehensive_report


def main():
    """Run the Level 3 Safety demonstration."""
    print_separator("Level 3 Safety - Pre-deployment Testing and Runtime Monitoring", "=", 80)

    print("This demonstration shows the complete Safety_MAS workflow:")
    print("  1. Pre-deployment safety testing")
    print("  2. Runtime safety monitoring")
    print("  3. Test-monitor integration")
    print()

    # Create the MAS
    print("Creating research assistant MAS...")
    try:
        mas = create_research_assistant_mas_with_wrapper()
        print(f"MAS created with {len(mas.get_agents())} agents")
        print()
    except Exception as e:
        print(f"Error creating MAS: {e}")
        print("Please ensure AG2/AutoGen is installed and LLM configuration is set.")
        return

    # Create Safety_MAS wrapper
    print("Creating Safety_MAS wrapper...")
    try:
        safety_mas = Safety_MAS(mas)
        print(f"Safety_MAS created successfully")
        print(f"  Available risk tests: {len(safety_mas.risk_tests)}")
        print(f"  Available monitors: {len(safety_mas.monitor_agents)}")
        print()
    except Exception as e:
        print(f"Error creating Safety_MAS: {e}")
        import traceback
        traceback.print_exc()
        return

    # Run Module 1: Pre-deployment Testing
    try:
        test_results = module1_pre_deployment_testing(safety_mas)
    except Exception as e:
        print(f"Error in Module 1: {e}")
        import traceback
        traceback.print_exc()
        test_results = {}

    # Run Module 2: Runtime Monitoring
    try:
        alerts = module2_runtime_monitoring(safety_mas)
    except Exception as e:
        print(f"Error in Module 2: {e}")
        import traceback
        traceback.print_exc()
        alerts = []

    # Run Module 3: Test-Monitor Integration
    try:
        comprehensive_report = module3_test_monitor_integration(safety_mas)
    except Exception as e:
        print(f"Error in Module 3: {e}")
        import traceback
        traceback.print_exc()
        comprehensive_report = {}

    # Final summary
    print_separator("Level 3 Safety Demonstration Complete", "=", 80)

    print("Summary of demonstration:")
    print(f"  Module 1 (Pre-deployment Testing): {len(test_results)} tests executed")
    print(f"  Module 2 (Runtime Monitoring): {len(alerts)} alerts generated")
    print(f"  Module 3 (Test-Monitor Integration): Comprehensive report generated")
    print()
    print("The Safety_MAS framework provides:")
    print("  - Pre-deployment vulnerability assessment")
    print("  - Real-time safety monitoring during execution")
    print("  - Integrated test-monitor feedback loop")
    print("  - Comprehensive safety reporting")
    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
